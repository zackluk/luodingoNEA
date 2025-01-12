document.addEventListener('DOMContentLoaded', () => {
    playAudioOnLoad();
    setupButtonClickListeners();
    setupSpeechRecognition();
});

function setupButtonClickListeners() {
    document.querySelectorAll('button[name="word"]').forEach((button) => {
        button.addEventListener('click', function () {
        const word = button.value + " "; // Add space for separation

        button.classList.add('inactive')
        //disable button when clicked
        
        if (/^[!.,?;:(){}[\]'"`~@#$%^&*_+=<>|-]/.test(button.value)){
            const textBox = document.getElementById('text-box');
            const text = textBox.value;
            textBox.value = text.trim();
            //removes ending whitespace, if the current character is a punctuation
        };
        
        addString(word);
        createNewButton(word.trim());
        });
    });
}

function setupSpeechRecognition() {
    const speechTitle = document.getElementById('speech-title');
    if (speechTitle) {
        const enableRecognition = speechTitle.getAttribute('data-enable-recognition') === 'true';

        if (enableRecognition){
            let recognition;
            let isListening = false;
            const transcriptionElement = document.getElementById('transcription');
            const toggleButton = document.getElementById('toggle-speech');
            const clearButton = document.getElementById('clear-transcription');

            if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window){
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                recognition = new SpeechRecognition();

                recognition.lang = 'de-DE';  // Set language to German (Germany)
                recognition.continuous = true;  // Continuously listens
                recognition.interimResults = true;  // Show intermediate results

                // Handle speech recognition results
                recognition.onresult = (event) => {
                    let transcript = '';
                    for (const result of event.results){
                        transcript += result[0].transcript;  // Add each 'result' to the transcript
                    }

                    // Update transcription display
                    transcriptionElement.innerText = transcript;

                    // Set transcription in the text box
                    const textBox = document.getElementById('text-box');
                    textBox.value = transcript;

                    // Send transcription to backend
                    fetch('/transcribe', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ text: transcript })  // Send transcription as JSON
                    });
                };

                // Handle recognition errors
                recognition.onerror = (event) => {
                    console.error('Speech recognition error', event.error);
                };
            } else {
                alert('SpeechRecognition is not supported on your browser.');
            }

            // Handle start/stop of speech recognition on button click
            toggleButton.onclick = (event) => {
                event.preventDefault();  // Prevent form submission

                if (isListening) {
                    // Stop recognition when it is listening
                    recognition.stop();
                    toggleButton.classList.remove('listening'); // Remove 'listening' class
                    toggleButton.classList.add('not-listening'); // Add 'not-listening' class
                    isListening = false;  // Toggle listening state
                } else {
                    // Start recognition when not listening
                    recognition.start();
                    toggleButton.classList.remove('not-listening'); // Remove 'not-listening' class
                    toggleButton.classList.add('listening'); // Add 'listening' class
                    isListening = true;  // Toggle listening state
                }

                // Ensure transcription is updated before toggling listening state
                const transcription = transcriptionElement.innerText.trim();  // Get trimmed transcription text
                const textBox = document.getElementById('text-box');
                textBox.value = transcription;  // Set transcription into the text box
            };

            // Handle the Clear Transcription button click
            clearButton.onclick = (event) => {
                event.preventDefault();

                // Clear the transcription display and text box
                transcriptionElement.innerText = '';  // Clear transcription text
                const textBox = document.getElementById('text-box');
                textBox.value = '';  // Clear the input field
            };
        }
    }
}

function playAudioOnLoad() {
    var audio = document.getElementById('audio');
    if (audio) {
        // Wait until the audio is ready to play
        audio.oncanplaythrough = function() {
            audio.play().catch(function(error) {
                console.log('Error playing audio:', error);
            });
        };

        // Try playing immediately if possible
        audio.play().catch(function(error) {
            console.log('Autoplay failed:', error);
        });
    } else {
        console.log('Audio element not found!');
    }
}


function confirmExit() {
    return confirm("Are you sure you don't want to finish the lesson? All progress will be lost.")
}

function addString(string){
    const textBox = document.getElementById('text-box');
    // getting the items within the textbox I believe
    
    const start = textBox.selectionStart;
    const end = textBox.selectionEnd;
    const text = textBox.value;

    // Insert the accent at the cursor position
    textBox.value = text.substring(0, start) + string + text.substring(end);

    // Place the cursor after the inserted accent
    textBox.selectionStart = textBox.selectionEnd = start + string.length;

    // Bring focus back to the text box
    textBox.focus();
}

function removeString(string) {
    const textBox = document.getElementById('text-box');
    const currentText = textBox.value.trim().split(' ');

    // Find the first occurrence of the string and remove it
    const index = currentText.indexOf(string);
    if (index !== -1) {
        currentText.splice(index, 1); // Remove the first occurrence
    }

    // Update the text box with the remaining words
    textBox.value = currentText.join(' ') + " ";
}

function createNewButton(string) {
    const buttonContainer = document.getElementById('button-container');

    const newButton = document.createElement('button');
    newButton.type = 'button';
    newButton.textContent = string;
    newButton.value = string;
    newButton.classList.add('mouse-nav-button')

    const defaultButton = Array.from(document.querySelectorAll('.mouse-nav-default-button-container button')).find(button => button.value === string);

    newButton.addEventListener('click', function () {
        buttonContainer.removeChild(newButton);
        removeString(newButton.value);

        if (defaultButton){
            defaultButton.classList.remove('inactive');
        }
    });

    buttonContainer.appendChild(newButton);

    if (defaultButton){
        defaultButton.classList.add('inactive');
    }
}

function selectOption(value){
    const userInput = document.getElementById('selectedOption');
    userInput.value = value;
    //directly setting the value of the input to be the one of the new selected option
}

function submitForm(){
    //new function to submit form, so that the check button can just exist in the footer
    document.getElementById('questionForm').submit();
}