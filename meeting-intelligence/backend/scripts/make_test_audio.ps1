Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.SetOutputToWaveFile("data/test_speech.wav")
$synth.Speak("Alice will finish the report by Friday. Bob agreed to review the API design next week.")
$synth.Dispose()
Write-Output "Created data/test_speech.wav"
