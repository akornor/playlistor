const CeleryProgressBar = (function() {
  function onSuccessDefault(
    progressBarElement,
    progressBarMessageElement,
    data
  ) {
    progressBarElement.style.backgroundColor = "#76ce60";
    progressBarMessageElement.innerHTML = `<a target="_blank" href="${data.result}">${data.result}</a>`;
    resetButton();
  }

  function onErrorDefault(progressBarElement, progressBarMessageElement) {
    progressBarElement.style.backgroundColor = "#dc4f63";
    progressBarMessageElement.innerHTML = "Uh-Oh, something went wrong!";
    resetButton();
  }

  function onProgressDefault(
    progressBarElement,
    progressBarMessageElement,
    progress
  ) {
    progressBarElement.style.backgroundColor = "#68a9ef";
    progressBarElement.style.width = progress.percent + "%";
    progressBarMessageElement.innerHTML =
      progress.current + " of " + progress.total + " songs processed.";
  }

  function updateProgress(progressUrl, options) {
    options = options || {};
    const progressBarId = options.progressBarId || "progress-bar";
    const progressBarMessage =
      options.progressBarMessageId || "progress-bar-message";
    const progressBarElement =
      options.progressBarElement || document.getElementById(progressBarId);
    const progressBarMessageElement =
      options.progressBarMessageElement ||
      document.getElementById(progressBarMessage);
    const onProgress = options.onProgress || onProgressDefault;
    const onSuccess = options.onSuccess || onSuccessDefault;
    const onError = options.onError || onErrorDefault;
    const pollInterval = options.pollInterval || 500;

    fetch(progressUrl).then(function(response) {
      response.json().then(function(data) {
        if (data.progress) {
          onProgress(
            progressBarElement,
            progressBarMessageElement,
            data.progress
          );
        }
        if (!data.complete) {
          setTimeout(updateProgress, pollInterval, progressUrl, options);
        } else {
          if (data.success) {
            onSuccess(progressBarElement, progressBarMessageElement, data);
          } else {
            onError(progressBarElement, progressBarMessageElement);
          }
        }
      });
    });
  }
  return {
    onSuccessDefault: onSuccessDefault,
    onErrorDefault: onErrorDefault,
    onProgressDefault: onProgressDefault,
    updateProgress: updateProgress,
    initProgressBar: updateProgress // just for api cleanliness
  };
})();
