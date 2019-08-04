const $ = (window.$ = document.querySelector.bind(document));

let button = $("#btn");

const resetProgressBar = () => {
  $("#progress-bar").style.width = "0%";
  $("#progress-bar-message").innerHTML = "";
};
// this is probably hacky
//should figure out a better way to reset button
const resetButton = () => {
  button.innerHTML = "Convert";
  button.disabled = false;
};

button.onclick = async function(event) {
  event.preventDefault();
  const playlist = $("#playlist").value;
  if (playlist === "") {
    return;
  }
  if (!is_valid_url(playlist.trim())) {
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
  try {
    const response = await fetch("/playlist", {
      method: "POST",
      body: JSON.stringify({
        playlist
      }),
      headers: {
        "Content-Type": "application/json"
      }
    });
    if (!response.ok) {
      throw Error(response.statusText);
    }
    let { task_id } = await response.json();
    const progressUrl = `/celery-progress/${task_id}/`;
    CeleryProgressBar.initProgressBar(progressUrl);
  } catch (error) {
    CeleryProgressBar.onErrorDefault();
  }
};
const is_valid_url = str => {
  const regexp = /^(?:(?:https?):\/\/)?(?:(?!(?:10|127)(?:\.\d{1,3}){3})(?!(?:169\.254|192\.168)(?:\.\d{1,3}){2})(?!172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2})(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5])){2}(?:\.(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-4]))|(?:(?:[a-z\u00a1-\uffff0-9]-*)*[a-z\u00a1-\uffff0-9]+)(?:\.(?:[a-z\u00a1-\uffff0-9]-*)*[a-z\u00a1-\uffff0-9]+)*(?:\.(?:[a-z\u00a1-\uffff]{2,})))(?::\d{2,5})?(?:\/\S*)?$/;
  return regexp.test(str);
};
