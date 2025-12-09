// OTP Auto Move Logic
const inputs = document.querySelectorAll('.otp-input');
const hiddenField = document.getElementById('otpHidden');

inputs.forEach((input, index) => {
    input.addEventListener('input', () => {
        if (input.value.length === 1 && index < inputs.length - 1) {
            inputs[index + 1].focus();
        }
    });

    input.addEventListener('keydown', (e) => {
        if (e.key === "Backspace" && !input.value && index > 0) {
            inputs[index - 1].focus();
        }
    });
});

// Before submitting form → combine OTP digits into hidden field
document.getElementById("otpForm").addEventListener("submit", () => {
    hiddenField.value = Array.from(inputs).map(i => i.value).join('');
});
