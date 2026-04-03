# Answer_Sheet_Evaluator
An answer evaluation system that extracts handwritten or typed student responses using OCR and automatically grades them using semantic similarity.

This project is a comprehensive web-based application designed to automate the evaluation of subjective student answers using advanced artificial intelligence techniques. Developed with the Flask framework, it simplifies the traditional grading process by allowing teachers to upload questions along with model answers and evaluate student responses submitted as images or PDF files.

The system leverages Google's Gemini API to perform Optical Character Recognition (OCR), accurately extracting text from uploaded answer sheets without altering the original content. This ensures that spelling, grammar, and writing style remain unchanged, maintaining the authenticity of student responses. The extracted text is then analyzed using Sentence-BERT (SBERT), a powerful Natural Language Processing (NLP) model that converts text into vector embeddings. These embeddings are compared with model answers using cosine similarity to determine how closely the student’s response matches the expected answer.

Based on predefined similarity thresholds, the application automatically assigns marks, making it capable of evaluating answers even when students use different wording but convey the same meaning. Additionally, the system includes a spell-checking feature that highlights misspelled words, helping teachers quickly identify language errors in responses.

To provide flexibility, the platform allows manual score adjustments, enabling educators to add or deduct marks as needed. All evaluation results are organized and can be downloaded in CSV format for further analysis or as a PDF report for easy sharing and record-keeping. The system supports multiple file formats, including PNG, JPG, JPEG, and PDF, making it suitable for a wide range of use cases.

With session management to handle user interactions and maintain workflow continuity, the application ensures a smooth experience from question upload to final result generation.
