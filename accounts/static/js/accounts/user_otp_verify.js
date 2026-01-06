document.addEventListener('DOMContentLoaded', function () {
    // ... [Your OTP Auto Move Logic stays exactly the same] ...
    const inputs = document.querySelectorAll('.otp-input');
    const hiddenField = document.getElementById('otpHidden');
    const otpForm = document.getElementById("otpForm");

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

    if (otpForm) {
        otpForm.addEventListener("submit", () => {
            hiddenField.value = Array.from(inputs).map(i => i.value).join('');
        });
    }

    // ----------------- MODIFIED OTP Timer Logic -----------------

    let expiryTimestamp = window.otpExpiry ? Math.floor(window.otpExpiry) : 0;

    const timerElement = document.getElementById('time');
    const timerContainer = document.getElementById('otp-timer');
    const resendSection = document.getElementById('resend-section');
    
    // NEW: Target the specific resend button inside the section
    const resendButton = resendSection ? resendSection.querySelector('button') : null;

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

            // Disable OTP inputs when time is up
            document.querySelectorAll('.otp-input').forEach(input => input.disabled = true);
            
            // Disable the "Verify" button
            const submitBtn = document.querySelector('.btn-custom');
            if (submitBtn) submitBtn.disabled = true;

            // --- THE KEY MODIFICATION ---
            if (resendSection) {
                resendSection.style.display = 'block'; // Show the section
                if (resendButton) resendButton.disabled = false; // ENABLE the resend button
            }

        } else {
            // --- WHILE TIMER IS RUNNING ---
            if (resendSection) {
                resendSection.style.display = 'none'; // Hide the section
                if (resendButton) resendButton.disabled = true; // KEEP IT DISABLED
            }
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