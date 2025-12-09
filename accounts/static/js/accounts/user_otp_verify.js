document.addEventListener('DOMContentLoaded', function () {
    // OTP Auto Move Logic
    const inputs = document.querySelectorAll('.otp-input');
    const hiddenField = document.getElementById('otpHidden');
    const otpForm = document.getElementById("otpForm");

    inputs.forEach((input, index) => {
        input.addEventListener('input', () => {
            // Auto move to the next field
            if (input.value.length === 1 && index < inputs.length - 1) {
                inputs[index + 1].focus();
            }
        });

        input.addEventListener('keydown', (e) => {
            // Auto move to the previous field on backspace
            if (e.key === "Backspace" && !input.value && index > 0) {
                inputs[index - 1].focus();
            }
        });
    });

    // Before submitting form → combine OTP digits into hidden field
    if (otpForm) {
        otpForm.addEventListener("submit", () => {
            hiddenField.value = Array.from(inputs).map(i => i.value).join('');
        });
    }

    // ----------------- OTP Timer Logic -----------------

    // Default to 0 if the variable is not passed or is invalid.
    // We expect window.otpExpiry to be set in the HTML template
    let expiryTimestamp = 0;

    if (window.otpExpiry) {
        expiryTimestamp = Math.floor(window.otpExpiry);
    }

    const timerElement = document.getElementById('time');
    const timerContainer = document.getElementById('otp-timer');
    const resendSection = document.getElementById('resend-section');

    function updateTimer() {
        const now = Date.now() / 1000;
        let remaining = Math.floor(expiryTimestamp - now);

        if (remaining < 0) remaining = 0;

        const minutes = Math.floor(remaining / 60);
        const seconds = remaining % 60;

        if (timerElement) {
            timerElement.textContent = `${minutes}:${seconds < 10 ? '0' : ''}${seconds}`;
        }

        if (remaining <= 0) {
            clearInterval(timerInterval);
            if (timerElement) timerElement.textContent = "Expired";

            if (timerContainer) timerContainer.classList.add('text-danger');

            document.querySelectorAll('.otp-input').forEach(input => input.disabled = true);
            const submitBtn = document.querySelector('.btn-custom');
            if (submitBtn) submitBtn.disabled = true;

            if (resendSection) resendSection.style.display = 'block';

        } else {
            if (resendSection) resendSection.style.display = 'none';
        }
    }

    let timerInterval;
    if (expiryTimestamp > 0 && timerContainer) {
        updateTimer();
        timerInterval = setInterval(updateTimer, 1000);
    } else if (timerContainer) {
        timerContainer.style.display = 'none';
    }
});
