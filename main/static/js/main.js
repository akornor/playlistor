const $ = (window.$ = document.querySelector.bind(document));

const button = $("#btn");

const resetProgressBar = () => {
  $("#progress-bar").style.width = "0%";
  $("#progress-bar-message").innerHTML = "";
};
// this is probably hacky
//should figure out a better way to reset button
const resetButton = () => {
  let button = $("#btn");
  button.innerHTML = "Submit 👍🏽";
  button.disabled = false;
};

button.onclick = event => {
  event.preventDefault();
  const playlist = $("#playlist").value;
  if (!is_valid_url(playlist)) {
    swal(
      "Invalid URL",
      "Enter valid url e.g https://itunes.apple.com/us/playlist/ep-3-paak-house-radio-playlist/pl.be45d23328f642cc91cf7086c7126daf"
    );
    return;
  }
  // clear progress bar
  resetProgressBar();
  button.innerHTML = "<i class='fa fa-spinner fa-spin '></i>";
  button.disabled = true;
  fetch("/playlist", {
    method: "POST",
    body: JSON.stringify({
      playlist: playlist
    }),
    headers: {
      "Content-Type": "application/json"
    }
  })
    .then(response => {
      response.json().then(data => {
        if ('task_id' in data) {
          const progressUrl = `/celery-progress/${data.task_id}/`;
          // console.log(progressUrl);
          CeleryProgressBar.initProgressBar(progressUrl);
        } else {
          CeleryProgressBar.onErrorDefault();
        }
      });
    })
    .catch(err => {
      console.log(err);
    });
};
const is_valid_url = str => {
  const regexp = /^(?:(?:https?):\/\/)?(?:(?!(?:10|127)(?:\.\d{1,3}){3})(?!(?:169\.254|192\.168)(?:\.\d{1,3}){2})(?!172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2})(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5])){2}(?:\.(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-4]))|(?:(?:[a-z\u00a1-\uffff0-9]-*)*[a-z\u00a1-\uffff0-9]+)(?:\.(?:[a-z\u00a1-\uffff0-9]-*)*[a-z\u00a1-\uffff0-9]+)*(?:\.(?:[a-z\u00a1-\uffff]{2,})))(?::\d{2,5})?(?:\/\S*)?$/;
  return regexp.test(str.trim());
};
