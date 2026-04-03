#Required libraries
import io
import csv
import re
from flask import Flask, render_template, request, redirect, session, Response, send_file
from flask_session import Session
from werkzeug.utils import secure_filename
from PIL import Image
from pdf2image import convert_from_bytes
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from spellchecker import SpellChecker

#Configuration
app = Flask(__name__, template_folder="templates")
app.secret_key = "secure-key-123"

app.config["SESSION_TYPE"] = "filesystem"
Session(app)

#Api Connection
genai.configure(api_key="your-api-key")

#Teacher login and credentials
TEACHER = {
    "admin": "admin123",
    "teacher1": "vb123",
    "teacher2": "ts456"
}

#Allowed extensions/files
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

#Sbert model loading
sbert = SentenceTransformer("all-MiniLM-L6-v2")

#Spell checker
spell = SpellChecker()

#Function to highlight misspelled words
def highlight_misspelled(text):

    words = text.split()
    highlighted = []

    for word in words:

        clean_word = re.sub(r'[^a-zA-Z]', '', word).lower()

        if clean_word and clean_word not in spell:
            highlighted.append(f"<span style='color:red;font-weight:bold'>{word}</span>")
        else:
            highlighted.append(word)

    return " ".join(highlighted)

#Login Page
@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        if TEACHER.get(username) == password:
            session["user"] = "teacher"
            return redirect("/upload_questions")

    return render_template("login.html")

#Upload Questions
@app.route("/upload_questions", methods=["GET", "POST"])
def upload_questions():

    if "user" not in session:
        return redirect("/")

    if request.method == "POST":

        questions = request.form.getlist("question")
        models = request.form.getlist("model_answer")
        marks_raw = request.form.getlist("max_marks")

        marks = [int(m) if m.strip().isdigit() else 0 for m in marks_raw]

        question_bank = []

        for q, m, mod in zip(questions, marks, models):
            if q.strip():
                question_bank.append({
                    "question": q,
                    "max_marks": m,
                    "model_answer": mod
                })

        session.pop("results", None)
        session["question_bank"] = question_bank

        return redirect("/upload_answers")

    return render_template("upload_questions.html")

#OCR FUNCTION
def extract_answers(file, question):

    filename = secure_filename(file.filename)
    ext = filename.rsplit(".", 1)[1].lower()

    images = []

    if ext in ["png", "jpg", "jpeg"]:
        images.append(Image.open(file))

    elif ext == "pdf":
        pages = convert_from_bytes(file.read())
        images.extend(pages)

    extracted_text = ""

    model = genai.GenerativeModel("gemini-2.5-flash")

    for img in images:

        prompt = f"""
        Extract only the student's answer for the following question.

        You are performing OCR.
        Extract the student's answer exactly as written in the image.

        IMPORTANT RULES:
        - Copy the text exactly as it appears.
        - Do NOT correct spelling mistakes.
        - Do NOT correct grammar.
        - Do NOT paraphrase or summarize.
        - Do NOT add any extra words.

        Question:
        {question}

        Return only the answer text.
        """

        try:

            response = model.generate_content([prompt, img])

            #UPDATED RESPONSE HANDLING
            if response and hasattr(response, "text") and response.text:
                text = response.text

            elif response and response.candidates:
                text = response.candidates[0].content.parts[0].text

            else:
                text = ""

            extracted_text += text.strip() + " "

        except Exception as e:
            print("OCR Error:", e)

    print("Extracted Answer:", extracted_text)  # DEBUG

    return extracted_text.strip()

#SBERT GRADING
def sbert_grade(model_ans, student_ans, max_marks):

    if not student_ans:
        print("Student answer empty")
        return 0, 0.0

    emb = sbert.encode([model_ans, student_ans])

    sim = cosine_similarity([emb[0]], [emb[1]])[0][0]

    print("Similarity:", sim)  # DEBUG

    if sim >= 0.85:
        score = max_marks
    elif sim >= 0.70:
        score = int(max_marks * 0.8)
    elif sim >= 0.55:
        score = int(max_marks * 0.6)
    elif sim >= 0.40:
        score = int(max_marks * 0.4)
    else:
        score = 0

    return score, float(sim)

#Upload Answers
@app.route("/upload_answers", methods=["GET", "POST"])
def upload_answers():

    if "user" not in session or "question_bank" not in session:
        return redirect("/upload_questions")

    question_bank = session["question_bank"]

    if request.method == "POST":

        roll_no = request.form.get("roll_no")

        all_results = session.get("results", [])

        for idx, q in enumerate(question_bank):

            file = request.files.get(f"file_{idx}")

            if file and allowed_file(file.filename):

                ans = extract_answers(file, q["question"])

                highlighted_ans = highlight_misspelled(ans)

                score, sim = sbert_grade(
                    q["model_answer"],
                    ans,
                    q["max_marks"]
                )

                all_results.append({

                    "student": roll_no,
                    "question": q["question"],
                    "ocr_answer": highlighted_ans,
                    "model_answer": q["model_answer"],
                    "similarity": round(sim, 3),
                    "score": score,
                    "max": q["max_marks"]

                })

        session["results"] = all_results

        return redirect("/results")

    return render_template("upload_answers.html", questions=question_bank)

#Results
@app.route("/results")
def results():

    rows = session.get("results", [])

    return render_template("results.html", rows=rows)

#GRACE MARK ADJUSTMENT
@app.route("/adjust_score", methods=["POST"])
def adjust_score():

    index = int(request.form["index"])
    change = int(request.form["change"])

    results = session.get("results", [])

    if 0 <= index < len(results):

        results[index]["score"] += change

        if results[index]["score"] < 0:
            results[index]["score"] = 0

        if results[index]["score"] > results[index]["max"]:
            results[index]["score"] = results[index]["max"]

    session["results"] = results

    return redirect("/results")

#CSV DOWNLOAD
@app.route("/download_csv")
def download_csv():

    rows = session.get("results", [])

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Roll No",
        "Question",
        "OCR Answer",
        "Model Answer",
        "Similarity",
        "Score",
        "Max"
    ])

    for r in rows:
        writer.writerow([
            r["student"],
            r["question"],
            r["ocr_answer"],
            r["model_answer"],
            r["similarity"],
            r["score"],
            r["max"]
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=results.csv"}
    )

#PDF DOWNLOAD
@app.route("/download_pdf")
def download_pdf():

    rows = session.get("results", [])

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    y = 800

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, y, "Evaluation Results")

    y -= 30

    for r in rows:

        if y < 120:
            pdf.showPage()
            y = 800

        pdf.setFont("Helvetica", 10)

        pdf.drawString(50, y, f"Roll No: {r['student']}")
        y -= 14

        pdf.drawString(60, y, f"Score: {r['score']} / {r['max']}")
        y -= 14

        pdf.drawString(60, y, f"Similarity: {r['similarity']}")
        y -= 20

    pdf.save()

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="results.pdf",
        mimetype="application/pdf"
    )

#LOGOUT
@app.route("/logout")
def logout():

    session.clear()
    return redirect("/")

#RUN
if __name__ == "__main__":
    app.run(debug=True)