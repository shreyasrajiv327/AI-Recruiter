# AI-Powered E-Recruitment Platform

## Overview

The AI-Powered E-Recruitment Platform is designed to streamline the hiring process by leveraging automation and machine learning technologies. It features resume screening, chatbot interviews, candidate management, and automated email communication, helping recruiters manage candidates efficiently.

## Features

- **Resume Screening**: Automatically evaluates resumes using AI-powered algorithms to match candidates based on job requirements.
- **Chatbot Interviews**: Conducts preliminary candidate interviews using an AI chatbot, providing immediate feedback and insights to recruiters.
- **Candidate Management**: Easily track and manage candidates throughout the recruitment process, from application to final decision.
- **Automated Email Communication**: Sends automatic emails to candidates to keep them informed at various stages of the recruitment process.

## Technologies Used

- **Backend**: Flask, OpenAI API
- **Frontend**: React.js
- **Database**: MongoDB
- **Programming Languages**: Python, JavaScript
- **Deployment**: Docker, Heroku

## Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/your-repo/e-recruitment-platform.git
   cd e-recruitment-platform
   ```

2. **Backend Setup**
   * Install dependencies for the Flask backend:
     ```bash
     cd backend
     pip install -r requirements.txt
     ```
   * Set up environment variables for OpenAI API, MongoDB connection, and email service:
     ```bash
     export OPENAI_API_KEY=your_openai_api_key
     export MONGO_URI=your_mongo_uri
     export EMAIL_HOST=your_email_host
     export EMAIL_PORT=your_email_port
     ```
   * Run the Flask backend:
     ```bash
     flask run
     ```

3. **Frontend Setup**
   * Navigate to the `frontend` folder and install dependencies:
     ```bash
     cd ../frontend
     npm install
     ```
   * Start the React app:
     ```bash
     npm start
     ```

4. **Run Both Frontend and Backend**
   * Once both the backend and frontend are running, access the platform at `http://localhost:3000`.

## Project Members

* **Reethu RG Thota**
* **Shreyas Rajiv**
* **SR Monish Raj**

## Usage

1. **Resume Screening**: Upload a resume in PDF format for automatic evaluation.
2. **Chatbot Interviews**: Interact with the AI chatbot for the first-round interview.
3. **Candidate Management**: Add, edit, and manage candidates through the dashboard.
4. **Automated Email Communication**: Customize email templates and send updates to candidates.

## Future Enhancements

* Integration with external job boards for job postings.
* Advanced analytics and reporting for recruitment insights.
* Video interview functionality.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with detailed information on your changes.

## License

This project is licensed under the MIT License. See the LICENSE file for details.
