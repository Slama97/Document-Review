# import necessary python libraries/packages
import io
import os
import uuid
import json
import streamlit as st
from dotenv import load_dotenv
from openai import AzureOpenAI
#from utils import display_messages, calculate_cost, send_prompt_to_assistant
import openai
import time




def upload_to_openai(filepath):
    """Upload a file to OpenAI and return its file ID."""
    with open(filepath, "rb") as file:
        response = client.files.create(file=file, purpose="assistants")
    return response

def calculate_cost(prompt_tokens, completion_tokens):
    """Calculate the cost based on GPT-4o token usage."""
    # Cost rates:
    gpt4_input_rate = 2.50 / 1_000_000  # $2.50 per 1 million input tokens
    gpt4_output_rate = 7.50 / 1_000_000  # $10.00 per 1 million output tokens

    # Calculate cost based on the tokens used
    input_cost = prompt_tokens * gpt4_input_rate
    output_cost = completion_tokens * gpt4_output_rate
    
    return input_cost + output_cost

# Helper function to ensure no duplicate messages are appended
def is_message_duplicate(message, messages):
    """Check if the message is already in the session state."""
    for existing_message in messages:
        if existing_message["role"] == message["role"] and existing_message["content"] == message["content"]:
            return True
    return False

# Helper function to display all messages (user, assistant, system), ensuring no duplication
def display_messages(messages):
    """Display all messages (user, assistant, system), but only once."""
    displayed_messages = set()  # Keep track of displayed messages to avoid duplicates
    for message in messages:
        if message.get("content") and (message["role"], message["content"]) not in displayed_messages:
            with st.chat_message(message["role"]):  # Role determines message type
                st.markdown(f'<p style="font-size: 16px;">{message["content"]}</p>', unsafe_allow_html=True)
            displayed_messages.add((message["role"], message["content"]))  # Mark message as displayed
            


# Load environment variables from .env file
#load_dotenv(dotenv_path='.env')

# Set up proxy environment variables to access external websites
#os.environ['http_proxy'] = os.getenv('HTTP_PROXY')
#os.environ['https_proxy'] = os.getenv('HTTP_PROXY')

# Initialize the AzureOpenAI client
client = AzureOpenAI(
    api_key=os.getenv('AZURE_OPENAI_API_KEY'),
    api_version=os.getenv('API_VERSION'),
    azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT')
)

# Set the page title for the whole app
st.set_page_config(
    page_title="Dokument Review",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Top expandable bar for instructions (collapsed by default)
with st.expander("Einführung & Anweisungen", expanded=False):
    st.markdown("""
        # Willkommen beim **Dokumenten-Review-Tool**! 🎉

        Dieses Tool hilft Ihnen dabei, Dokumente mithilfe eines KI-assistierten Überprüfungsprozesses zu analysieren. Sie können verschiedene Kriterien wie Geheimhaltungsstufe, Unterlagenklasse, Dateiformat und viele andere überprüfen lassen. Laden Sie Ihre Dateien hoch, und lassen Sie die KI die Prüfung automatisch durchführen.

        ## So funktioniert's:

        1. **Datei hochladen**:
            - Gehen Sie in der **Sidebar** und laden Sie eine Datei hoch, die Sie überprüfen möchten (z. B. PDF, TXT, CSV, DOCX, XLSX).
        
        2. **Bereits hochgeladene Dateien**:
            - Unter **"Hochgeladene Dateien"** sehen Sie alle Dokumente, die bereits hochgeladen wurden.
            - Wenn Sie eines der hochgeladenen Dokumente zur Überprüfung auswählen möchten, klicken Sie einfach auf den Dateinamen. Das ausgewählte Dokument wird dann **grün** hervorgehoben, um anzuzeigen, dass es für die Überprüfung bereit ist.
            - Wenn Sie die Auswahl des Dokuments aufheben möchten, klicken Sie erneut auf den Dateinamen, und die Auswahl wird zurückgesetzt (die Farbe wird wieder **grau**).
        
        3. **Kriterien auswählen**:
            - Sie können wählen, welche Kriterien Sie überprüfen möchten. Die verfügbaren Prüfungen sind:
                - **Geheimhaltungsstufe**, **Unterlagenklasse**, **Dateiformat**
                - **Freigeber**, **Verantwortlichkeiten**
                - **Änderungshistorie**,**Status, Version und Baseline**, **Namenskonvention**
            - Die Prüfungen werden automatisch im Hintergrund durch die KI ausgeführt. Sie erhalten die **Antwort des Assistenten** direkt, ohne dass Sie sich um die Details der Ausführung kümmern müssen.
        
        4. **Ergebnisse und Visualisierungen**:
            - Alle geprüften Kriterien werden auf der **linken Seite** angezeigt. Jedes Kriterium wird entweder mit **grün** (i.O.) oder **rot** (n.i.O.) markiert, je nachdem, ob das Kriterium erfüllt wurde.
            - Unter der Visualisierung wird angezeigt, wie viele **Token** für die Eingabe und Ausgabe verbraucht wurden, sowie die **Kosten** für die verwendeten Tokens (Input und Output).

        5. **Weitere Funktionen**:
            - **Chat löschen**: Sie können den Chat jederzeit löschen, um eine neue Sitzung zu starten.
            - **Ergebnisse herunterladen**: Wenn die Überprüfung abgeschlossen ist, können Sie den **Bericht** der KI in Form einer **Textdatei** herunterladen, die alle Ergebnisse der Prüfung enthält.

        6. **Chat-Funktion**:
            - In der **Chat-Leiste** können Sie direkt mit dem Assistenten kommunizieren. Sie können Fragen stellen oder zusätzliche Informationen anfordern, und der Assistent wird Ihnen antworten.

        ## Wichtige Hinweise:
        - Wenn Sie nach der **KM ID** gefragt werden, stellen Sie sicher, dass Sie diese angeben, da sie für den Start der Überprüfung erforderlich ist.
        - Die **Kriterien** werden automatisch generiert und im Hintergrund abgearbeitet. Sie erhalten die endgültige Antwort des Assistenten ohne weitere Eingriffe.
        - Alle Ergebnisse und Statusanzeigen werden live aktualisiert, sodass Sie den Fortschritt der Überprüfung in Echtzeit verfolgen können.
    """, unsafe_allow_html=True)

# Add title with custom font size
st.markdown(
    """
    <h1 style="text-align: left; font-size: 48px;">📚🔍 <i>Dokumenten-Review mit LLM</i> 🤖💬</h1>
    """, 
    unsafe_allow_html=True
)

# --- Initial Setup for Azure OpenAI Service ---

# Import the assistants using the assistant IDs (Assistant were already created in Azure OpenAI Service)
assistant_id = "asst_UZ1evOoGrkD8D1IKOmik22z6"

security_bot = "asst_B5yqh4UUKlCKva3I7bvQOd7k"

chat_bot = "asst_EprYp6OVLH3WNcaWZbORPOfr"

vorgaben_bot = "asst_tOMJq7dsqHY5i1a1q7NnvzSu"

# Retrieve the list of all vector stores
vector_stores = client.beta.vector_stores.list()

# Check if "dokumen-review" exists in the list of vector stores
vector_store_name = "dokument review"
vector_store = None

# Search for the vector store in the list
for store in vector_stores.data:
    if store.name == vector_store_name:
        vector_store = store
        break

# If the vector store doesn't exist, create it
if vector_store is None:
    vector_store = client.beta.vector_stores.create(name=vector_store_name)
# Main content area with two columns
col2, col3 = st.columns([2, 1])  # Center (for chatbox) and Right (for visualizations)
with col3:
    st.subheader("Visualisierung der geprüften Kriterien:")
    
# --- Initial Setup for Interface with Streamlit ---
def initialize_session_state():
    """Initializes session state variables if not already set."""
    if "thread_id" not in st.session_state:
        thread = client.beta.threads.create()
        st.session_state.thread_id = thread.id

    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())

    if "messages" not in st.session_state: 
        st.session_state.messages = []
        
        message = {"role": "assistant", "content": """Willkommen in der Dokumenten-Review-App! Wie kann ich Ihnen heute behilflich sein ?
                      Falls Sie ein Dokument nach bestimmten formalen Kriterien überprüfen lassen möchten, teilen Sie mir bitte die KM-ID mit."""}
        
        st.session_state.messages.append(message)
        with col2:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                

    
    if "file_id_list" not in st.session_state:
        st.session_state.file_id_list = []
        
    if 'file_id_map' not in st.session_state:
        st.session_state.file_id_map = {}
        
    if 'current_assistant_id' not in st.session_state:        
        st.session_state.current_assistant_id = assistant_id

    # Initialize token usage and total cost if they don't exist
    if 'token_usage' not in st.session_state:
        st.session_state.token_usage = 0  # Initialize token usage to 0
    
    if 'total_cost' not in st.session_state:
        st.session_state.total_cost = 0.0  # Initialize total cost to 0.0
        
    # Initialize session state to keep track of uploaded files and selected criteria
    if 'criteria_selected' not in st.session_state:
        st.session_state.uploaded_files = []  # Store uploaded file names
        st.session_state.file_buttons = {}  # To store the state (color) of file buttons
        
    # Initialize criteria status in session state if it doesn't already exist
    if "criteria_status" not in st.session_state:
        st.session_state.criteria_status = {
            0: "lightgray",  # Geheimhaltungsstufe
            1: "lightgray",  # Unterlagenklasse
            2: "lightgray",   # Dateiformat
            3: "lightgray",  # Freigeber
            4: "lightgray"  # Verantwortlichkeit
    }

initialize_session_state()



# Define the criteria and their corresponding prompts
criteria = [
    {"name": "Geheimhaltungsstufe", "prompt": "Jetzt nur die Geheimhaltungsstufe prüfen. Als Antwort nur schreiben Geheimhaltungsstufe: i.O oder Geheimhaltungsstufe: n.i.O"},
    {"name": "Unterlagenklasse", "prompt": "Jetzt nur die Unterlagenklasse prüfen. Als Antwort nur schreiben Unterlagenklasse: i.O oder Unterlagenklasse: n.i.O"},
    {"name": "Dateiformat", "prompt": "Jetzt nur Dateiformat prüfen. Als Antwort nur schreiben Dateiformat: i.O oder Dateiformat: n.i.O"},
    {"name": "Freigeber", "prompt": "Jetzt nur die Aufgabe zur Überprüfung des Freigebers. Antwort muss zusammengefasst werden. Bitte fügen Sie in Ihrer Antwort „i.O“ oder „n.i.O“ ein."},
    {"name": "Verantwortlichkeit", "prompt": "Jetzt nur die Aufgabe zur Überprüfung der Verantwortlichkeiten. Antwort muss zusammengefasst werden. Bitte fügen Sie in Ihrer Antwort „i.O“ oder „n.O“ ein."},
    {"name": "Änderungshistorie Notwendigkeit", "prompt": "Jetzt nur die Aufgabe der Notwendigkeit der Änderungshistorie-Überprüfung gemäß Schritte in der Anleitung durchführen."},
    {"name": "Änderungshistorie Vollständigkeit", "prompt": "Jetzt nur die Aufgabe der Vollständigkeit der Änderungshistorie-Überprüfung gemäß Schritte in der Anleitung durchführen."},
    {"name": "Version und Status", "prompt": "Jetzt nur die aktuelle Version und Status des Review-Dokuments mir zeigen."},
    {"name": "Versionsprüfung", "prompt": "Jetzt nur Prüfung der Version. Anleitung nicht zurückgeben."},
    {"name": "Statusprüfung", "prompt": "Jetzt Prüfung vom Status."},
    {"name": "Baseline-Prüfung", "prompt": "Jetzt nur Baseline-Prüfung. "},
    {"name": "Namenskonvention", "prompt": "Jetzt nur die Aufgabe der Namenskonvention-Überprüfung durchführen. "}
]

# Define a function to update criteria status and display immediately
def update_criteria_status(index, response):
    # Update the criteria status based on the response
    if "n.i.O" in response:
        st.session_state.criteria_status[index] = "red"
    elif "i.O" in response:
        st.session_state.criteria_status[index] = "green"
    else:
        st.session_state.criteria_status[index] = "lightgray"  # Default when no valid response
    
    # Directly update the status visualization immediately after each check
    background_color = st.session_state.criteria_status[index]
    text_color = "white" if background_color == "green" or "red" else "black"

    with col3:
        #st.subheader("Visualisierung der geprüften Kriterien:")
        # Display the updated status for each criterion directly in col3
        st.markdown(f'''
            <div style="background-color:{background_color}; color:{text_color}; padding: 10px; border-radius: 5px; font-size:20px; margin-bottom: 10px;">
                {criteria[index]["name"]}
            </div>
        ''', unsafe_allow_html=True)

def send_prompt_to_assistant(prompt_text, assistant_id= st.session_state.current_assistant_id, display=True):
    """Send a prompt to the assistant, extract token usage, calculate the cost, and update the chat with the response."""
    # Ensure the assistant ID is set correctly in session state
    if st.session_state.current_assistant_id is None:
        st.error("Bitte wählen Sie zuerst einen Assistant.")
        return

    # Send the prompt to the assistant
    client.beta.threads.messages.create(
        thread_id=st.session_state.thread_id,
        role="user",
        content=prompt_text
    )

    run = client.beta.threads.runs.create(
        thread_id=st.session_state.thread_id,
        assistant_id=st.session_state.current_assistant_id,
    )

    # Poll for the run to complete and retrieve the assistant's messages
    while run.status != 'completed':
        time.sleep(1)
        run = client.beta.threads.runs.retrieve(
            thread_id=st.session_state.thread_id,
            run_id=run.id
        )

    # Access token usage directly from the run object
    usage_data = run.usage if hasattr(run, 'usage') else None

    if usage_data:
        token_usage = usage_data.total_tokens  # Extract total tokens used
        prompt_tokens = usage_data.prompt_tokens
        completion_tokens = usage_data.completion_tokens
    else:
        token_usage = 0  # Default if no usage data is available
        prompt_tokens = completion_tokens = 0

    st.session_state.token_usage += token_usage  # Increment the total tokens used

    # Calculate the cost based on token usage
    cost = calculate_cost(prompt_tokens, completion_tokens)
    st.session_state.total_cost += cost  # Increment the total cost

    # Retrieve all messages in the thread
    messages = client.beta.threads.messages.list(
        thread_id=st.session_state.thread_id
    )

    # Avoid appending duplicate assistant messages
    assistant_messages_for_run = [
        message for message in messages if message.run_id == run.id and message.role == "assistant"
    ]

    # Prepare the response text from assistant's message
    response = ""
    for message in assistant_messages_for_run:
        text_content = message.content[0].text.value if message.content else ''

        # Only append if the message is not already in session state
        if not is_message_duplicate({"role": "assistant", "content": text_content}, st.session_state.messages):
            st.session_state.messages.append({"role": "assistant", "content": text_content})

        response = text_content  # Assuming the last message is the response

    # Display all messages at once if 'display' is True
    if display:
        display_messages(st.session_state.messages)

    return response  # Return the response content

# Sidebar for controls (on the left)
with st.sidebar:
    st.title("📝Was möchten Sie tun ?")
    st.write("")  # Adds one empty line
    st.write("")  # Adds one empty line
    # Display the subheader with an info icon beside it
    st.markdown("""
        <h2 style="display:inline;">🔍Datei durchsuchen:</h2>
        <span style="cursor: pointer; font-size: 20px; margin-left: 10px;" title="Sie können Datei lokal durchsuchen und in der App hochladen.">
            ℹ️
        </span>
    """, unsafe_allow_html=True)
    # File uploader added to the sidebar
    uploaded_file = st.file_uploader("Laden Sie bitte eine Datei hoch:", type=["txt", "csv", "pdf", "xlsx","docx"])

    # When a file is uploaded, add it to the session state
    if uploaded_file is not None:
        file_name = uploaded_file.name
        if file_name not in st.session_state.uploaded_files:
            st.session_state.uploaded_files.append(file_name)
            st.session_state.file_buttons[file_name] = "lightgray"  # Default color for the file button

    # Display uploaded files with clickable buttons
    # Display the subheader with an info icon beside it
    st.write("")  # Adds one empty line
    st.markdown("""
        <h2 style="display:inline;">📂Hochgeladene Dateien:</h2>
        <span style="cursor: pointer; font-size: 20px; margin-left: 10px;" title="Sie können hier die hochgeladenen Dateien sehen. 
        Wenn Sie auf den Dateinamen klicken, wird die Datei dem Assistenten für ein formales Review zur Verfügung gestellt.
        DM-Plan_Tabelle wude schon für Sie hochgeladen.">
            ℹ️
        </span>
    """, unsafe_allow_html=True)
    # Special case for DM-Plan_Tabelle.xlsx, display as green background text without button
    st.markdown(f'''
        <div style="background-color:green; color:white; padding: 10px; border-radius: 5px; font-size:18px; margin-bottom: 10px;">
            DM-Plan_Tabelle.xlsx
        </div>
    ''', unsafe_allow_html=True)
    for file_name in st.session_state.uploaded_files:
        # Check if the button is clicked
        if st.button(file_name, key=file_name, use_container_width=True):
            # Handle when the file button is clicked, and it's not in use (lightgray)
            if st.session_state.file_buttons[file_name] == "lightgray":
                # Change the color to green after clicking
                st.session_state.file_buttons[file_name] = "green"
                            # Then send the check criteria prompt
                prompt = """Das Artefakt wurde aktualisiert. Bitte löschen und vergessen Sie 
                alle zuvor bewerteten Kriterien und setzen Sie alle vorherigen Bewertungen zurück. Sie müssen erstaml das neue Artefakt öffnen
                und fagen Sie nochmal nach der KM ID, um eine Prüfung zu starten."""
                with col2:
                    response = send_prompt_to_assistant(prompt, display = False)
                    
                # Save the file locally when clicked
                with open(file_name, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                # Upload the file to OpenAI when clicked
                file = upload_to_openai(file_name)
                st.session_state.file_id_list.append(file.id)  # Store the file ID in session state

                # Store the relationship between file_name and file_id in the dictionary
                st.session_state.file_id_map[file_name] = file.id

                # Update the vector store with the new file
                batch_add = client.beta.vector_stores.file_batches.create(
                    vector_store_id=vector_store.id,
                    file_ids=[file.id]
                )
                time.sleep(1)

                # Update the assistant with the new file search tool resource
                assistant = client.beta.assistants.update(
                    assistant_id=assistant_id,
                    tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}}
                )

            # Handle when the button is clicked again and is already green (file in use)
            else:
                st.session_state.file_buttons[file_name] = "lightgray"  # Revert button color to light gray

                # Retrieve the file_id associated with the file_name from the file_id_map
                file_id_to_remove = st.session_state.file_id_map.get(file_name)

                if file_id_to_remove:
                    # Use the API method to delete a file from the vector store
                    response = client.beta.vector_stores.files.delete(                            
                        vector_store_id=vector_store.id,
                        file_id=file_id_to_remove
                    )
         
        # Display file button with dynamic color (green or lightgray)
        st.markdown(f'''
            <div style="background-color:{st.session_state.file_buttons[file_name]}; color:white; padding: 10px; border-radius: 5px; font-size:18px; margin-bottom: 10px;">
                {file_name}
            </div>
        ''', unsafe_allow_html=True)
    st.write("")  # Adds one empty line       
    st.subheader("✔️ Welche Kriterien wollen Sie prüfen:")
    

    # Show the first button for the first process
    if st.button("1️⃣ Prüfung Geheimhaltungsstufe, Unterlagenklasse, Dateiformat"):
        st.session_state.current_assistant_id = security_bot
        with col2:
            # Send initial prompt directly without KM ID
            initial_prompt = """KM ID: SUP1_001; jetzt nur den ersten Schritt durchführen: Review-Dokument: QS-Plan_probe.docx ist schon im Vektorspeicher vorhanden."""
            response = send_prompt_to_assistant(initial_prompt, st.session_state.current_assistant_id, False)

            # Check each criterion and update the status based on response
            G_prompt = criteria[0]["prompt"]
            G_response = send_prompt_to_assistant(G_prompt, st.session_state.current_assistant_id, False)
            update_criteria_status(0, G_response)

            U_prompt = criteria[1]["prompt"]
            U_response = send_prompt_to_assistant(U_prompt, st.session_state.current_assistant_id, False)
            update_criteria_status(1, U_response)

            D_prompt = criteria[2]["prompt"]
            D_response = send_prompt_to_assistant(D_prompt, st.session_state.current_assistant_id, False)
            update_criteria_status(2, D_response)

            # Ask the final question after all criteria checks are done
            last_prompt = """jetzt eine zusammenfassungstabelle mit allen fragen und Erklärung und Begründung. In """
            final_response = send_prompt_to_assistant(last_prompt, st.session_state.current_assistant_id)
            
    if st.button("2️⃣ Prüfung Namenskonvention, Status, Änderungshistorie, Baseline, Versionen"):
        st.session_state.current_assistant_id = vorgaben_bot
        with col2:
            # Send initial prompt directly without KM ID
            initial_prompt = """KM ID: SUP1_001; EcoRair_SUP.8_KM-Plan.pdf und Review-Dokument (QS-Plan_probe.docx) sind schon im Vektorspeicher vorhanden. """
            response = send_prompt_to_assistant(initial_prompt, st.session_state.current_assistant_id, False)

            # Check each criterion and update the status based on response
            A_prompt = criteria[5]["prompt"]
            A_response = send_prompt_to_assistant(A_prompt, st.session_state.current_assistant_id, False)
            update_criteria_status(5, A_response)

            B_prompt = criteria[6]["prompt"]
            B_response = send_prompt_to_assistant(B_prompt, st.session_state.current_assistant_id, False)
            update_criteria_status(6, B_response)

            C_prompt = criteria[7]["prompt"]
            C_response = send_prompt_to_assistant(C_prompt, st.session_state.current_assistant_id, False)
            update_criteria_status(7, C_response)
            
            D_prompt = criteria[8]["prompt"]
            D_response = send_prompt_to_assistant(D_prompt, st.session_state.current_assistant_id, False)
            update_criteria_status(8, D_response)

            E_prompt = criteria[9]["prompt"]
            E_response = send_prompt_to_assistant(E_prompt, st.session_state.current_assistant_id, False)
            update_criteria_status(9, E_response)
            
            F_prompt = criteria[10]["prompt"]
            F_response = send_prompt_to_assistant(F_prompt, st.session_state.current_assistant_id, False)
            update_criteria_status(10, F_response)
            
            G_prompt = criteria[11]["prompt"]
            G_response = send_prompt_to_assistant(G_prompt, st.session_state.current_assistant_id, False)
            update_criteria_status(11, G_response)
            # Ask the final question after all criteria checks are done
            last_prompt = """jetzt nur eine zusammenfassungstabelle mit allen fragen und Erklärung und Begründung."""
            final_response = send_prompt_to_assistant(last_prompt, st.session_state.current_assistant_id)
    # Show the second button for the second process
    if st.button("3️⃣ Prüfung Freigeber, Verantwortlichkeit"):
        # Proceed only if KM ID is removed
        st.session_state.current_assistant_id = chat_bot
        with col2:
            # Send initial prompt directly without KM ID
            initial_prompt = """KM ID: SUP1_001; ECORAIR_MAN.3_SEMP.pdf und Review-Dokument (QS_Plan_probe.docx) sind schon im Vektorspeicher vorhanden."""
            response = send_prompt_to_assistant(initial_prompt, st.session_state.current_assistant_id, False)
            
            # Check each criterion and update the status based on response
            G_prompt = criteria[3]["prompt"]
            G_response = send_prompt_to_assistant(G_prompt, st.session_state.current_assistant_id)
            update_criteria_status(3, G_response)

            U_prompt = criteria[4]["prompt"]
            U_response = send_prompt_to_assistant(U_prompt, st.session_state.current_assistant_id)
            update_criteria_status(4, U_response)
    
    st.write("")  # Adds one empty line
    st.subheader("🛠️ Weitere Funktionen:")
        
    # Clear chat button
    if st.button("Chat Löschen"):
        st.session_state.messages.clear()
        
    # Collect the assistant's messages
    assistant_messages = [
        message["content"] for message in st.session_state.messages
    ]

    # Check if there are any messages to download
    if assistant_messages:
        # Format messages as plain text
        messages_text = "\n\n".join(assistant_messages)
        
        # Create a BytesIO object for downloading the messages as a file
        message_file = io.BytesIO()
        message_file.write(messages_text.encode())
        message_file.seek(0)  # Reset the pointer to the beginning of the file
        
        # Provide the download button for the user
        st.download_button(
            label="Ergebnisse Herunterladen",
            data=message_file,
            file_name="Bericht.txt",  # Name of the file to be downloaded
            mime="text/plain"  # MIME type for text files
        )
    else:
        st.warning("Kein Bericht zum Herunterladen.")

# Center Column (the main chatbox in the middle)
with col2:   
    # Chat input for the user
    if prompt := st.chat_input("Deine Nachricht"):
        # Add user message to the state and display it
        st.session_state.messages.append({"role": "user", "content": prompt})
        #with st.chat_message("user"):
        #    st.markdown(prompt)
        
        res = send_prompt_to_assistant(prompt)

# Right Column (for visualizations and criteria selection stacked one under another)

    #criteria = ["Geheimhaltungsstufe", "Unterlagenklasse", "Dateiformat"]
    #for i, criterion in enumerate(criteria):
    #    background_color = st.session_state.criteria_status[i] = "lightgray"
    #    text_color = "black"
        
    #    st.markdown(f'''
    #        <div style="background-color:{background_color}; color:{text_color}; padding: 10px; border-radius: 5px; font-size:20px; margin-bottom: 10px;">
    #            {criterion}
    #        </div>
    #    ''', unsafe_allow_html=True) 

with col3:  
    # Display token usage and cost information with improved formatting
    st.subheader("Token-Nutzung und Kosten")

    # Display total token usage and total cost with nice formatting
    token_usage = st.session_state.token_usage
    total_cost = st.session_state.total_cost

    # Format the token usage and cost to make it clearer and more readable
    st.markdown(f"""
    <div style="background-color:#f0f0f5; padding: 15px; border-radius: 10px; font-size: 16px; margin-bottom: 15px;">
        <strong>Gesamt verwendete Token:</strong> <span style="font-weight: bold; font-size: 18px;">{token_usage}</span>
    </div>

    <div style="background-color:#e6f7ff; padding: 15px; border-radius: 10px; font-size: 16px; margin-bottom: 15px;">
        <strong>Gesamtkosten:</strong> <span style="font-weight: bold; font-size: 18px;">€{total_cost:.4f}</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.subheader("Zusätzliche Infos")

    st.markdown("""
    - Diese Anwendung nutzt Azure OpenAI für die Dokumentenprüfung. Weitere Infos: https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/assistants
    - Das Frontend wurde mit Streamlit entwickelt. Mehr erfahren: https://streamlit.io/
    - Die Nutzung basiert auf Tokens, Kosten variieren je nach Modell. Details: https://openai.com/api/pricing/
    """, unsafe_allow_html=True)
