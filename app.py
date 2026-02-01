import streamlit as st
import google.generativeai as genai
import time
import re
from PyPDF2 import PdfReader
import json

# --- 1. CONFIGURATION ---
try:
    genai.configure(api_key="AIzaSyBJRorRVentFsaotLNh8KCAYdw8exsQS2E")
    MODEL_ID = 'gemini-1.5-flash'
    model = genai.GenerativeModel(MODEL_ID)
except Exception as e:
    st.error("API Configuration Error. Check your API Key.")

st.set_page_config(page_title="AI Pro Interviewer", layout="wide")

# --- 2. HELPER FUNCTIONS ---
def extract_text_from_pdf(pdf_file):
    try:
        reader = PdfReader(pdf_file)
        return "".join([page.extract_text() for page in reader.pages])
    except:
        return "Resume text processed."

def parse_scores(feedback_text):
    scores = re.findall(r"(\d+)/10", feedback_text)
    if len(scores) >= 3:
        return [min(int(s), 10) for s in scores[:3]]
    return [6, 7, 7]

def generate_unique_question(used_questions, jd_text, resume_text, category, difficulty):
    """Generate a unique question that hasn't been asked before"""
    try:
        prompt = f"""As a professional interviewer, generate ONE unique {difficulty} difficulty {category} interview question.
        
        JOB DESCRIPTION CONTEXT:
        {jd_text[:500]}
        
        CANDIDATE'S RESUME CONTEXT:
        {resume_text[:500]}
        
        PREVIOUSLY ASKED QUESTIONS (DO NOT REPEAT THESE):
        {chr(10).join(used_questions) if used_questions else "None"}
        
        Generate a question that:
        1. Is relevant to the job description
        2. Considers the candidate's background from resume
        3. Is truly unique and not similar to previous questions
        4. Is appropriate for {difficulty} difficulty level
        5. Is specific and requires detailed answer
        
        Return ONLY the question text without any additional commentary."""
        
        response = model.generate_content(prompt)
        question = response.text.strip()
        return question
    except Exception as e:
        # Fallback questions based on category
        fallback_questions = {
            "Technical": [
                "Explain how you would optimize database queries for high-traffic applications.",
                "Describe your approach to handling security vulnerabilities in web applications.",
                "How do you ensure code scalability and maintainability in large projects?",
                "Explain the differences between microservices and monolithic architecture.",
                "Describe your experience with CI/CD pipelines and automation tools."
            ],
            "Behavioral": [
                "Describe a time when you had to persuade a team to adopt a technical approach they were initially opposed to.",
                "Tell me about a project where you faced significant scope creep and how you handled it.",
                "Describe a situation where you had to learn a new technology quickly to meet a deadline.",
                "How do you handle conflicts within your team when there are disagreements about technical decisions?",
                "Tell me about a time you failed at a project and what you learned from it."
            ],
            "Personal": [
                "What motivates you to excel in your technical work?",
                "How do you stay updated with the latest technologies and trends in our industry?",
                "Describe your ideal work environment and how it helps you perform at your best.",
                "What professional achievement are you most proud of and why?",
                "Where do you see yourself in your career in the next 3-5 years?"
            ]
        }
        
        # Get available questions for the category
        available = fallback_questions.get(category, ["Tell me about your relevant experience."])
        
        # Find a question not used before
        for q in available:
            if q not in used_questions:
                return q
        
        # If all fallbacks are used, create a variation
        return f"Based on your experience in {category.lower()} aspects, what unique challenge have you faced?"

def evaluate_answer(question, answer, jd_text, resume_text, category):
    """Evaluate answer with context from JD and resume"""
    try:
        prompt = f"""Evaluate this interview answer comprehensively and objectively.

        JOB REQUIREMENTS (from JD):
        {jd_text[:300]}

        CANDIDATE'S BACKGROUND (from Resume):
        {resume_text[:300]}

        QUESTION CATEGORY: {category}
        QUESTION: {question}
        CANDIDATE'S ANSWER: {answer}

        Please evaluate on these THREE dimensions (score each 0-10):
        1. KNOWLEDGE/RELEVANCE: How accurate, relevant, and knowledgeable is the answer? Does it demonstrate understanding of the topic?
        2. COMMUNICATION/STRUCTURE: How well-structured and clear is the response? Is it concise yet comprehensive?
        3. SPECIFICITY/EXAMPLES: Does the answer include specific examples, data, or evidence from experience?

        CRITICAL SCORING GUIDELINES:
        - Score 9-10: Exceptional answer with specific examples, directly relevant to JD, shows deep understanding
        - Score 7-8: Good answer with some relevant details, shows competence
        - Score 5-6: Average answer, generic, lacks specifics
        - Score 3-4: Poor answer, vague, shows limited understanding
        - Score 1-2: Very poor answer, irrelevant or incorrect
        - Score 0: No answer or completely off-topic

        IMPORTANT: Base scores STRICTLY on answer quality considering JD requirements. Be objective.

        Provide feedback in this EXACT format:
        KNOWLEDGE SCORE: X/10
        COMMUNICATION SCORE: Y/10
        SPECIFICITY SCORE: Z/10
        FEEDBACK: [Detailed feedback explaining scores and areas for improvement]"""
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return "KNOWLEDGE SCORE: 5/10\nCOMMUNICATION SCORE: 5/10\nSPECIFICITY SCORE: 5/10\nFEEDBACK: Evaluation system temporarily unavailable. Please continue."

# --- 3. STATE INITIALIZATION ---
if "step" not in st.session_state:
    st.session_state.step = "setup"
    st.session_state.difficulty = "Medium"
    st.session_state.score_card = []
    st.session_state.q_count = 0
    st.session_state.used_questions = []  # Track asked questions
    st.session_state.asked_indices = []  # Track fallback question indices

st.title("🚀 Hack2Hire: Smart AI Interviewer")

# --- PHASE: SETUP ---
if st.session_state.step == "setup":
    st.header("Step 1: Interview Configuration")
    col1, col2 = st.columns(2)
    with col1:
        resume_file = st.file_uploader("Upload Resume (PDF)", type="pdf")
        st.session_state.total_q = st.slider("Number of Questions:", 3, 10, 5)
        st.session_state.difficulty = st.selectbox(
            "Select Difficulty Level:",
            ["Easy", "Medium", "Hard", "Expert"]
        )
    with col2:
        jd_text = st.text_area("Paste Job Description (JD)", height=150)
        st.session_state.selected_cats = st.multiselect(
            "Select Focus Areas:",
            ["Technical", "Behavioral", "Personal"],
            default=["Technical", "Behavioral"]
        )
    
    if st.button("🚀 Start Interview"):
        if resume_file and jd_text:
            st.session_state.resume_text = extract_text_from_pdf(resume_file)
            st.session_state.jd_text = jd_text
            st.session_state.step = "interviewing"
            st.session_state.used_questions = []  # Reset for new session
            st.session_state.asked_indices = []  # Reset indices
            st.rerun()
        else:
            st.error("Please upload a resume and paste the job description.")

# --- PHASE: INTERVIEWING ---
elif st.session_state.step == "interviewing":
    st.sidebar.metric("Progress", f"{st.session_state.q_count + 1}/{st.session_state.total_q}")
    
    # Determine current category (rotate through selected categories)
    cat_index = st.session_state.q_count % len(st.session_state.selected_cats)
    current_cat = st.session_state.selected_cats[cat_index]
    
    # Generate new question if not exists
    if "current_q" not in st.session_state:
        try:
            question = generate_unique_question(
                st.session_state.used_questions,
                st.session_state.jd_text,
                st.session_state.resume_text,
                current_cat,
                st.session_state.difficulty
            )
            st.session_state.current_q = question
            st.session_state.used_questions.append(question)  # Track used question
        except Exception as e:
            st.error(f"Question generation error: {str(e)[:100]}")
            # Ultimate fallback
            fallbacks = {
                "Technical": "Explain the most challenging technical problem you've solved.",
                "Behavioral": "Describe a situation where you had to work with a difficult team member.",
                "Personal": "What drives your passion for this field of work?"
            }
            st.session_state.current_q = fallbacks.get(current_cat, "Tell me about your experience.")
        
        st.session_state.start_time = time.time()
        st.rerun()

    st.subheader(f"Round {st.session_state.q_count + 1}: {current_cat}")
    st.markdown(f"**Difficulty:** {st.session_state.difficulty}")
    st.info(st.session_state.current_q)
    
    user_ans = st.text_area(
        "Your Response:", 
        key=f"ans_{st.session_state.q_count}", 
        height=200,
        placeholder="Type your detailed answer here. Include specific examples from your experience..."
    )
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⏭️ Skip Question", use_container_width=True):
            st.session_state.score_card.append({
                "category": current_cat, 
                "question": st.session_state.current_q,
                "answer": "SKIPPED", 
                "feedback": "Question was skipped.",
                "time": time.time() - st.session_state.start_time,
                "scores": {"Knowledge": 0, "Communication": 0, "Clarity": 0}
            })
            st.session_state.q_count += 1
            del st.session_state.current_q
            if st.session_state.q_count >= st.session_state.total_q:
                st.session_state.step = "results"
            else:
                st.rerun()
    
    with col2:
        if st.button("✅ Submit Answer", type="primary", use_container_width=True):
            if not user_ans.strip():
                st.warning("Please provide an answer before submitting.")
            else:
                duration = time.time() - st.session_state.start_time
                
                with st.spinner("Evaluating your answer..."):
                    feedback = evaluate_answer(
                        st.session_state.current_q,
                        user_ans,
                        st.session_state.jd_text,
                        st.session_state.resume_text,
                        current_cat
                    )
                
                # Parse scores from feedback
                k_match = re.search(r"KNOWLEDGE SCORE:\s*(\d+)/10", feedback, re.IGNORECASE)
                c_match = re.search(r"COMMUNICATION SCORE:\s*(\d+)/10", feedback, re.IGNORECASE)
                s_match = re.search(r"SPECIFICITY SCORE:\s*(\d+)/10", feedback, re.IGNORECASE)
                
                k_score = int(k_match.group(1)) if k_match else 5
                c_score = int(c_match.group(1)) if c_match else 5
                s_score = int(s_match.group(1)) if s_match else 5
                
                # Extract feedback text
                feedback_text = ""
                if "FEEDBACK:" in feedback:
                    feedback_text = feedback.split("FEEDBACK:", 1)[1].strip()
                else:
                    # Try to find feedback after scores
                    lines = feedback.split('\n')
                    for i, line in enumerate(lines):
                        if any(x in line.upper() for x in ['FEEDBACK', 'COMMENT', 'ANALYSIS']):
                            feedback_text = '\n'.join(lines[i+1:]).strip()
                            break
                    if not feedback_text:
                        feedback_text = feedback
                
                st.session_state.score_card.append({
                    "category": current_cat, 
                    "question": st.session_state.current_q,
                    "answer": user_ans, 
                    "feedback": feedback_text,
                    "time": round(duration, 1),
                    "scores": {"Knowledge": k_score, "Communication": c_score, "Clarity": s_score}
                })
                
                st.session_state.q_count += 1
                del st.session_state.current_q
                
                if st.session_state.q_count >= st.session_state.total_q:
                    st.session_state.step = "results"
                else:
                    st.rerun()

# --- PHASE: RESULTS ---
elif st.session_state.step == "results":
    st.header("📊 Performance Analytics Dashboard")
    
    if not st.session_state.score_card:
        st.warning("No interview data available.")
        if st.button("Start New Interview"):
            st.session_state.clear()
            st.rerun()
    else:
        # Calculate averages
        total_questions = len(st.session_state.score_card)
        answered_questions = [d for d in st.session_state.score_card if d['answer'] != "SKIPPED"]
        
        if answered_questions:
            avg_k = sum(d['scores']['Knowledge'] for d in answered_questions) / len(answered_questions)
            avg_c = sum(d['scores']['Communication'] for d in answered_questions) / len(answered_questions)
            avg_cl = sum(d['scores']['Clarity'] for d in answered_questions) / len(answered_questions)
        else:
            avg_k = avg_c = avg_cl = 0
        
        # Overall score
        overall_score = round((avg_k + avg_c + avg_cl) / 3, 1)
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Overall Score", f"{overall_score}/10")
        with col2:
            st.metric("Questions Answered", f"{len(answered_questions)}/{total_questions}")
        with col3:
            st.metric("Avg. Knowledge", f"{avg_k:.1f}/10")
        with col4:
            avg_time = sum(d['time'] for d in answered_questions) / len(answered_questions) if answered_questions else 0
            st.metric("Avg. Time/Answer", f"{avg_time:.1f}s")
        
        # Progress bars
        st.subheader("Skill Assessment")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write("🧠 **Knowledge & Relevance**")
            st.progress(avg_k / 10)
            st.caption(f"{avg_k:.1f}/10")
        with col2:
            st.write("🗣️ **Communication & Clarity**")
            st.progress(avg_c / 10)
            st.caption(f"{avg_c:.1f}/10")
        with col3:
            st.write("💎 **Specificity & Examples**")
            st.progress(avg_cl / 10)
            st.caption(f"{avg_cl:.1f}/10")
        
        # Detailed feedback section
        st.subheader("📝 Detailed Question Feedback")
        
        for i, item in enumerate(st.session_state.score_card):
            with st.expander(f"Q{i+1}: {item['category']} - Score: {sum(item['scores'].values())/3:.1f}/10", expanded=(i==0)):
                col_a, col_b = st.columns([1, 1])
                with col_a:
                    st.markdown("**Question:**")
                    st.info(item['question'])
                    if item['answer'] == "SKIPPED":
                        st.warning("⚠️ Question was skipped")
                    else:
                        st.markdown("**Your Answer:**")
                        st.text_area("", item['answer'], height=100, key=f"answer_{i}", disabled=True)
                with col_b:
                    st.markdown("**Scores:**")
                    scores = item['scores']
                    col_s1, col_s2, col_s3 = st.columns(3)
                    with col_s1:
                        st.metric("Knowledge", f"{scores['Knowledge']}/10")
                    with col_s2:
                        st.metric("Communication", f"{scores['Communication']}/10")
                    with col_s3:
                        st.metric("Clarity", f"{scores['Clarity']}/10")
                    
                    st.markdown("**Feedback:**")
                    st.write(item['feedback'])
                    st.caption(f"Time taken: {item['time']} seconds")
        
        # Performance analysis
        st.subheader("📈 Performance Analysis")
        
        # Prepare data for charts
        categories = [item['category'] for item in st.session_state.score_card]
        knowledge_scores = [item['scores']['Knowledge'] for item in st.session_state.score_card]
        comm_scores = [item['scores']['Communication'] for item in st.session_state.score_card]
        
        import pandas as pd
        chart_data = pd.DataFrame({
            'Question': [f"Q{i+1}" for i in range(len(st.session_state.score_card))],
            'Knowledge': knowledge_scores,
            'Communication': comm_scores,
            'Time (s)': [item['time'] for item in st.session_state.score_card]
        })
        
        col_chart1, col_chart2 = st.columns(2)
        with col_chart1:
            st.bar_chart(chart_data.set_index('Question')[['Knowledge', 'Communication']])
        with col_chart2:
            st.line_chart(chart_data.set_index('Question')['Time (s)'])
        
        # Recommendations
        st.subheader("🎯 Recommendations for Improvement")
        
        if overall_score >= 8:
            st.success("Excellent performance! You demonstrated strong knowledge, communication skills, and provided specific examples.")
        elif overall_score >= 6:
            st.info("Good performance. Consider adding more specific examples and details to your answers.")
        elif overall_score >= 4:
            st.warning("Average performance. Focus on providing more structured answers with concrete examples from your experience.")
        else:
            st.error("Needs improvement. Practice structuring your answers with clear explanations and relevant examples.")
        
        # Action buttons
        col_btn1, col_btn2, col_btn3 = st.columns(3)
        with col_btn1:
            if st.button("🔄 Start New Interview", use_container_width=True):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
        with col_btn2:
            if st.button("📥 Export Results", use_container_width=True):
                results_data = {
                    "overall_score": overall_score,
                    "detailed_feedback": st.session_state.score_card,
                    "averages": {
                        "knowledge": avg_k,
                        "communication": avg_c,
                        "clarity": avg_cl
                    }
                }
                st.download_button(
                    label="Download JSON",
                    data=json.dumps(results_data, indent=2),
                    file_name="interview_results.json",
                    mime="application/json"
                )
        with col_btn3:
            if st.button("📊 View Summary", use_container_width=True):
                st.balloons()
                st.success(f"Interview completed! Final Score: {overall_score}/10")