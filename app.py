# import the python libraries/packages
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
    """Calculate the cost based on GPT-4 token usage."""
    # Cost rates based on the provided values:
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
            
def send_prompt_to_assistant(prompt_text, display=True):
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

# Load environment variables from .env file
load_dotenv(dotenv_path='.env')

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
assistant_id = "asst_rmoX2f3DDs2b2gz11XFdkPlS"



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
        
        # add initial message
        message = {"role": "assistant", "content": "Wilkommen in Dokumenten-Review app, wie kann ich heute behilflich sein?"}
        
        st.session_state.messages.append(message)
        with col2:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
            
    if "file_id_list" not in st.session_state:
        st.session_state.file_id_list = []  # Initialize the file_id_list to an empty list
        
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
        st.session_state.criteria_selected = [False, False, False]  # Criteria states: False = unchecked
        st.session_state.uploaded_files = []  # Store uploaded file names
        st.session_state.file_buttons = {}  # To store the state (color) of file buttons
    if "criteria_status" not in st.session_state:
        st.session_state.criteria_status = [None, None, None]
initialize_session_state()




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
    if st.button("1️⃣ Prüfung Geheimhaltungsstufe, Unterlagenklasse, Dateiformat"):
        with col2:
            # Send initial message for KM ID
            #initial_prompt = "Bitte sagen Sie die KM ID für das Review-Dokument:"
            #st.session_state.messages.append({"role": "user", "content": initial_prompt})
            #display_assistant_messages(st.session_state.messages)  # Display assistant's message immediately after processing
            #send_prompt_to_assistant(criteria_prompt)
            # Then send the check criteria prompt
            initial_prompt = """Der DM-Plan ist im Code-Interpreter angehängt, und das Artefakt ist 
            in der Dateisuche des Vektorspeichers (dokument review) angehängt.
            Öffne das Artefakt im Vektorspeicher und schreibe den Namen vom Artefakt.
            Dann nach KM ID fragen, wenn nicht vom bereits Benutzer eingegben ist.
            jetzt nur den ersten Schritt durchführen.
            """
            response = send_prompt_to_assistant(initial_prompt, display=False)
            # Step 2: Send prompt for Geheimhaltungsstufe
            G_prompt = """Jetzt nur die Geheimhaltungsstufe prüfen. Als Antwort nur schreiben Geheimhaltungsstufe: i.O oder Geheimhaltungsstufe: n.i.O"""
            G_response = send_prompt_to_assistant(G_prompt, display=False)

            if "n.i.O" in response:
                st.session_state.criteria_status[index] = "red"
            elif "i.O" in response:
                st.session_state.criteria_status[index] = "green"
            else:
                st.session_state.criteria_status[index] = "lightgray"  # Default when no valid response
            

            # Step 3: Send prompt for Unterlagenklasse
            U_prompt = """Jetzt nur die Unterlagenklasse prüfen. Als Antwort nur schreiben Unterlagenklasse: i.O oder Unterlagenklasse: n.i.O"""
            U_response = send_prompt_to_assistant(U_prompt, display=False)

            if "n.i.O" in response:
                st.session_state.criteria_status[index] = "red"
            elif "i.O" in response:
                st.session_state.criteria_status[index] = "green"
            else:
                st.session_state.criteria_status[index] = "lightgray"  # Default when no valid response
            

            # Step 4: Send prompt for Dateiformat
            D_prompt = """Jetzt nur Dateiformat prüfen. Als Antwort nur schreiben Dateiformat: i.O oder Dateiformat: n.i.O"""
            D_response = send_prompt_to_assistant(D_prompt, display=False)

            if "n.i.O" in response:
                st.session_state.criteria_status[index] = "red"
            elif "i.O" in response:
                st.session_state.criteria_status[index] = "green"
            else:
                st.session_state.criteria_status[index] = "lightgray"  # Default when no valid response
            
            last_prompt = """Falls KM ID  nicht bekannt, nur nochmal fragen nach KM ID fragen. 
            Ansonsten nur eine Zusammenfassungstabelle gemäß **Antwort_Template**
            zurückgeben mit Erklärung und Begründung. Die Ergebnisse von den Antworten davor nicht zurückgeben"""
            response = send_prompt_to_assistant(last_prompt)
            
            

    if st.button("2️⃣ Prüfung Namenskonvention, Status, Änderungshistorie, Baseline, Versionen"):
        pass
    if st.button("3️⃣ Prüfung Freigeber, Verantwortlichkeit"):
        pass
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
with col3:
    st.subheader("Visualisierung der geprüften Kriterien:")
    criteria = ["Geheimhaltungsstufe", "Unterlagenklasse", "Dateiformat"]
    for i, criterion in enumerate(criteria):
        background_color = st.session_state.criteria_status[i] if st.session_state.criteria_status[i] else "lightgray"
        text_color = "white" if background_color == "green" or "red" else "black"
        
        st.markdown(f'''
            <div style="background-color:{background_color}; color:{text_color}; padding: 10px; border-radius: 5px; font-size:20px; margin-bottom: 10px;">
                {criterion}
            </div>
        ''', unsafe_allow_html=True)


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
    
    # Additional info or controls
    st.subheader("Zusätzliche Infos")

    st.markdown("""
    - Diese Anwendung nutzt Azure OpenAI für die Dokumentenprüfung. Weitere Infos: https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/assistants
    - Das Frontend wurde mit Streamlit entwickelt. Mehr erfahren: https://streamlit.io/
    - Die Nutzung basiert auf Tokens, Kosten variieren je nach Modell. Details: https://openai.com/api/pricing/
    """, unsafe_allow_html=True)
