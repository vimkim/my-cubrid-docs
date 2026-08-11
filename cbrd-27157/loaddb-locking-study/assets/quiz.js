// CBRD-27157 loaddb locking study
document.addEventListener("DOMContentLoaded", () => {
  const quizzes = document.querySelectorAll("[data-quiz]");

  quizzes.forEach((quiz) => {
    const button = quiz.querySelector("[data-check-quiz]");
    const score = quiz.querySelector("[data-quiz-score]");

    if (!button || !score) {
      return;
    }

    button.addEventListener("click", () => {
      const questions = quiz.querySelectorAll("fieldset[data-answer]");
      let correctCount = 0;

      questions.forEach((question) => {
        const selected = question.querySelector("input[type='radio']:checked");
        const feedback = question.querySelector("[data-feedback]");
        const expected = question.dataset.answer;
        const explanation = question.dataset.explanation;

        feedback.classList.remove("correct", "incorrect");

        if (!selected) {
          feedback.textContent = "답을 고른 뒤 다시 채점해 보세요.";
          return;
        }

        if (selected.value === expected) {
          correctCount += 1;
          feedback.textContent = `맞았습니다. ${explanation}`;
          feedback.classList.add("correct");
        } else {
          feedback.textContent = `다시 생각해 보세요. ${explanation}`;
          feedback.classList.add("incorrect");
        }
      });

      score.textContent = `${questions.length}문제 중 ${correctCount}문제를 맞혔습니다.`;
    });
  });
});
