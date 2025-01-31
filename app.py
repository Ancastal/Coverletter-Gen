"""An application to generate cover letters based on user information and job postings."""
import streamlit as st
from src.cover_letter import scrape_job_posting, query, user_persona
from src.cover_letter_editor import CoverLetterEditor
import subprocess
import sys
import os
import time
import re
import json
import toml
from pathlib import Path
import warnings

warnings.filterwarnings("ignore")

try:
    from linkedin_api import Linkedin
except ModuleNotFoundError as e:
    subprocess.Popen([f'{sys.executable} -m pip install git+https://github.com/tomquirk/linkedin-api.git'], shell=True)
    time.sleep(90)

def save_secrets(secrets):
    """Save secrets to .streamlit/secrets.toml file."""
    secrets_path = Path('.streamlit/secrets.toml')
    secrets_path.parent.mkdir(exist_ok=True)
    with open(secrets_path, 'w') as f:
        toml.dump(secrets, f)

def load_secrets():
    """Load secrets from .streamlit/secrets.toml file."""
    try:
        return dict(st.secrets)
    except:
        return {}

# Custom CSS
def load_css():
    """Load and apply custom CSS styles"""
    with open("static/styles.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
        
# Page configuration
st.set_page_config(
    page_title='Cover Letter Generator',
    page_icon=':page_with_curl:',
    layout='centered',
    initial_sidebar_state='expanded'
)



def validate_linkedin_url(url, type="job"):
    """Validate LinkedIn URL format."""
    if not url:
        return False
    
    if type == "job":
        pattern = r'https?://(www\.)?linkedin\.com/jobs/view/\d+'
    else:  # profile
        pattern = r'https?://(www\.)?linkedin\.com/in/[\w\-]+'

    
    return bool(re.match(pattern, url))

def scrape_profile(profile_id):
    """Scrape LinkedIn profile with proper error handling."""
    try:
        # First try secrets
        email = st.secrets['LINKEDIN_EMAIL']
        pwd = st.secrets['LINKEDIN_PASSWORD']
    except Exception:
        # Fallback to environment variables
        email = os.getenv('LINKEDIN_EMAIL')
        pwd = os.getenv('LINKEDIN_PASSWORD')
        if not email or not pwd:
            raise ValueError("LinkedIn credentials not found in secrets or environment variables")

    try:
        api = Linkedin(email, pwd)
        profile = api.get_profile(profile_id)
        name = f"{profile['firstName']} {profile['lastName']}"
        education = [
            f"{edu['schoolName']} ({edu['timePeriod']['startDate']['year']}) - {edu.get('description', 'No description available')}"
            for edu in profile.get('education', [])
        ]
        experience = [
            f"{exp['title']} at {exp['companyName']} - {exp.get('description', 'No description available')}"
            for exp in profile.get('experience', [])
        ]
        certifications = [
            f"{cert['name']} from {cert['authority']}"
            for cert in profile.get('certifications', [])
        ]
        skills = [skill['name'] for skill in api.get_profile_skills(profile_id)]
        
        return user_persona.UserPersona(name, education, experience, skills, certifications)
    except Exception as e:
        raise Exception(f"Failed to scrape LinkedIn profile: {str(e)}")

def main():
    # Sidebar for app information
    with st.sidebar:
        st.title("ℹ️ About")
        st.markdown("""
        This app helps you generate professional cover letters using:
        - Your LinkedIn profile or manual input
        - Job posting details
        - AI-powered content generation
        
        **Note:** For privacy and security, use the local version for automatic profile scraping.
        """)
        
        st.markdown("---")
        st.caption("Made with ❤️ using Streamlit")

    load_css()
    # Main content
    st.title('Cover Letter Generator :page_with_curl:')
    
    badge_html = f"""
    <span style="
        display: inline-block;
        background-color: #ECF9EC;
        color: #1B7F1B;
        border: 1px solid #1B7F1B;
        border-radius: 4px;
        padding: 2px 6px;
        font-size: 0.85em;">
    v{open('VERSION').read()}
    </span>
    """
    
    st.markdown(badge_html, unsafe_allow_html=True)
    st.write('Generate personalized cover letters based on your profile and job postings.')
    st.markdown("""
            <div class="card pt-serif">
                <p><strong>Hi, I'm Antonio. 👋</strong></p>
                <p>I'm a PhD candidate in Artificial Intelligence at the University of Pisa, working on Creative Machine Translation with LLMs.</p>
                <p>My goal is to develop translation systems that can preserve style, tone, and creative elements while accurately conveying meaning across languages.</p>
                <p>Learn more about me at <a href="https://www.ancastal.com" target="_blank">www.ancastal.com</a></p>
            </div>
    """, unsafe_allow_html=True)
    # Create tabs for different input methods
    tabs = ["🔗 LinkedIn Integration", "✍️ Manual Input", "⚙️ Settings"]
    if 'cover_letter' in st.session_state and st.session_state.cover_letter is not None:
        tabs.append("📝 Editor")
    
    all_tabs = st.tabs(tabs)
    tab1, tab2, tab3, *editor_tab = all_tabs
    
    # Initialize session state for storing the generated cover letter
    if 'cover_letter' not in st.session_state:
        st.session_state.cover_letter = None
    if 'editor_active' not in st.session_state:
        st.session_state.editor_active = False

    with tab1:
        st.info("Currently, only LinkedIn job postings are supported (e.g., https://www.linkedin.com/jobs/view/3544765357/)")
        
        # Job Posting URL input with validation
        job_url = st.text_input('Job Posting URL', key='job_url', placeholder='https://www.linkedin.com/jobs/view/3544765357/')
        if job_url and not validate_linkedin_url(job_url, "job"):
            st.error("Please enter a valid LinkedIn job posting URL")
        
        # Profile URL input with validation
        profile_url = st.text_input('Your LinkedIn Profile URL', key='profile_url', placeholder='https://www.linkedin.com/in/johndoe/')
        if profile_url and not validate_linkedin_url(profile_url, "profile"):
            st.error("Please enter a valid LinkedIn profile URL")
            
        # Display generated content if available
        if 'cover_letter' in st.session_state and st.session_state.cover_letter is not None:
            st.markdown('<div class="success-message">✨ Your cover letter is ready!</div>', unsafe_allow_html=True)
            st.markdown("""<div class="cover-letter-container">
                        <p>{}</p>
                        </div>""".format(st.session_state.cover_letter['text']), unsafe_allow_html=True)
            
            st.markdown('<div class="download-button">', unsafe_allow_html=True)
            st.download_button(
                label="📥 Download Cover Letter",
                data=st.session_state.cover_letter['text'],
                file_name="cover_letter.txt",
                mime="text/plain",
                key='download_button2'
            )
            st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input('Full Name', placeholder='John Doe')
            education_level = st.selectbox('Education Level', 
                ['High School', 'Associate Degree', 'Bachelor\'s Degree', 'Master\'s Degree', 'PhD'])
        
        with col2:
            fields = [
                'Computer Science', 'Engineering', 'Business', 'Finance', 'Marketing',
                'Data Science', 'Healthcare', 'Education', 'Other'
            ]
            education_field = st.selectbox('Field of Study', fields)
            
        experience = st.text_area('Work Experience', 
            placeholder="Describe your relevant work experience...",
            help="Include your job titles, companies, and key achievements")
            
        skills = st.multiselect('Skills',
            ['Python', 'SQL', 'Java', 'JavaScript', 'C#', 'C++', 'PHP', 'Swift', 'Rust',
             'Data Analysis', 'Project Management', 'Communication', 'Leadership'],
            help="Select all relevant skills")
            
        certifications = st.multiselect('Certifications',
            ['AWS', 'Google Cloud', 'Azure', 'Cisco', 'CompTIA', 'PMP', 'CISSP'],
            help="Select any relevant certifications")
            
        # Display generated content if available
        if 'cover_letter' in st.session_state and st.session_state.cover_letter is not None:
            st.markdown('<div class="success-message">✨ Your cover letter is ready!</div>', unsafe_allow_html=True)
            st.markdown("""<div class="cover-letter-container">
                        <p>{}</p>
                        </div>""".format(st.session_state.cover_letter['text']), unsafe_allow_html=True)
            
            st.markdown('<div class="download-button">', unsafe_allow_html=True)
            st.download_button(
                label="📥 Download Cover Letter",
                data=st.session_state.cover_letter['text'],
                file_name="cover_letter.txt",
                mime="text/plain"
            )
            st.markdown('</div>', unsafe_allow_html=True)

    with tab3:
        st.info("Configure your application secrets here.")
        
        # Load current secrets
        current_secrets = load_secrets()
        
        # LinkedIn credentials section
        linkedin_email = st.text_input(
            "LinkedIn Email",
            value=current_secrets.get('LINKEDIN_EMAIL', ''),
            type='default'
        )
        linkedin_password = st.text_input(
            "LinkedIn Password",
            value=current_secrets.get('LINKEDIN_PASSWORD', ''),
            type='password'
        )
        
        if st.button("Save Settings"):
            try:
                new_secrets = {
                    'LINKEDIN_EMAIL': linkedin_email,
                    'LINKEDIN_PASSWORD': linkedin_password
                }
                save_secrets(new_secrets)
                st.success("Settings saved successfully!")
            except Exception as e:
                st.error(f"Failed to save settings: {str(e)}")

    # Only show editor tab if it exists
    if editor_tab:  # This checks if the list is not empty
        with editor_tab[0]:
            if st.session_state.cover_letter is not None:
                editor = CoverLetterEditor()
                edited_text = editor.create_editing_interface(st.session_state.cover_letter['text'])
                
                if edited_text != st.session_state.cover_letter['text']:
                    st.session_state.cover_letter['text'] = edited_text
                    st.markdown('<div class="success-message">✨ Cover letter updated successfully!</div>', unsafe_allow_html=True)
                    
                st.markdown("""<div class="cover-letter-container">
                            <p>{}</p>
                            </div>""".format(edited_text), unsafe_allow_html=True)
                
                # Add download button with centered styling
                st.markdown('<div class="download-button">', unsafe_allow_html=True)
                st.download_button(
                    label="📥 Download Cover Letter",
                    data=edited_text,
                    file_name="cover_letter.txt",
                    mime="text/plain",
                    key='download_button0'
                )
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info("Generate a cover letter first to use the editor.")

    # Generate button
    if st.button('Generate Cover Letter', type='primary'):
        with st.spinner("Generating your cover letter..."):
            try:
                # Get user data based on selected tab
                if tab1.active:  # LinkedIn Integration tab
                    if not job_url:
                        st.error("Please enter a job posting URL")
                        return
                    if not profile_url:
                        st.error("Please enter your LinkedIn profile URL")
                        return
                    profile_id = profile_url.rstrip('/').split('/')[-1]
                    user = scrape_profile(profile_id)
                else:  # Manual Input tab
                    if not name or not experience:
                        st.error("Please fill in all required fields")
                        return
                    education = f"{education_level} in {education_field}"
                    user = user_persona.UserPersona(name, education, experience, skills, certifications)

                # Generate cover letter
                job_posting = scrape_job_posting(job_url)
                response = query(user, job_posting, 'src/prompts/cover_letter.txt')
                
                # Store the generated cover letter in session state
                st.session_state.cover_letter = response
                st.session_state.editor_active = True

                # Display success message and cover letter in the active tab
                st.markdown('<div class="success-message">✨ Your cover letter is ready!</div>', unsafe_allow_html=True)
                st.markdown("""<div class="cover-letter-container">
                            <p>{}</p>
                            </div>""".format(response['text']), unsafe_allow_html=True)
                
                # Add download button with centered styling
                st.markdown('<div class="download-button">', unsafe_allow_html=True)
                st.download_button(
                    label="📥 Download Cover Letter",
                    data=response['text'],
                    file_name="cover_letter.txt",
                    mime="text/plain",
                    key='download_button1'
                )
                st.markdown('</div>', unsafe_allow_html=True)

                # Rerun to update the tabs structure
                time.sleep(0.5)  # Small delay to ensure UI updates
                st.rerun()
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                if "credentials not found" in str(e):
                    st.info("Please use the manual input method or run the app locally for LinkedIn integration.")

if __name__ == '__main__':
    main()
