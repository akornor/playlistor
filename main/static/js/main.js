const $ = (window.$ = document.querySelector.bind(document));

let button = $("#btn");

const SPOTIFY_PLAYLIST_URL_REGEX = /open\.spotify\.com\/(user\/.+\/)?playlist\/.+/;
const APPLE_MUSIC_PLAYLIST_URL_REGEX = /music\.apple\.com\/.+\/playlist\/.+/;
const SUPPORTED_PLATFORMS_PLAYLIST_URL_REGEX = /open\.spotify\.com\/(user\/.+\/)?playlist\/.+|music\.apple\.com\/.+\/playlist\/.+/;

const is_valid_url = str => {
  const regexp = /^(?:(?:https?):\/\/)?(?:(?!(?:10|127)(?:\.\d{1,3}){3})(?!(?:169\.254|192\.168)(?:\.\d{1,3}){2})(?!172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2})(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5])){2}(?:\.(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-4]))|(?:(?:[a-z\u00a1-\uffff0-9]-*)*[a-z\u00a1-\uffff0-9]+)(?:\.(?:[a-z\u00a1-\uffff0-9]-*)*[a-z\u00a1-\uffff0-9]+)*(?:\.(?:[a-z\u00a1-\uffff]{2,})))(?::\d{2,5})?(?:\/\S*)?$/;
  return regexp.test(str);
};

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
function displaySpinner() {
  // clear progress bar
  resetProgressBar();
  button.innerHTML = "<i class='fa fa-spinner fa-spin '></i>";
  button.disabled = true;
}
function getDestinationPlatform(url) {
  if (SPOTIFY_PLAYLIST_URL_REGEX.test(url)) {
    return "apple-music";
  } else if (APPLE_MUSIC_PLAYLIST_URL_REGEX.test(url)) {
    return "spotify";
  } else {
    throw new Error("Platform not yet supported.");
  }
}

async function maybeExpandURL(url) {
  if (SUPPORTED_PLATFORMS_PLAYLIST_URL_REGEX.test(url)) {
    return url;
  }
  url = await expandURL(url);
  return url;
}

function raiseForStatus(response) {
  if (!response.ok) {
    throw new Error(response.statusText);
  }
}
async function expandURL(shortenedURL) {
  const response = await fetch("/expand", {
    method: "POST",
    body: JSON.stringify({
      url: shortenedURL
    }),
    headers: {
      "Content-Type": "application/json"
    }
  });
  raiseForStatus(response);
  const { url } = await response.json();
  return url;
}

button.onclick = async function(event) {
  event.preventDefault();
  const playlist = $("#playlist").value.trim();
  if (playlist === "") {
    return;
  }
  if (!is_valid_url(playlist)) {
    Swal.fire(
      "Invalid URL",
      "Enter valid url e.g https://itunes.apple.com/us/playlist/ep-3-paak-house-radio-playlist/pl.be45d23328f642cc91cf7086c7126daf"
    );
    return;
  }
  displaySpinner();
  const url = await maybeExpandURL(playlist);
  if (
    SPOTIFY_PLAYLIST_URL_REGEX.test(url) &&
    !MusicKit.getInstance().isAuthorized
  ) {
    resetButton();
    const result = await Swal.fire({
      title: "🚨Sign In🚨",
      html:
        "We noticed you're trying to convert Spotify ➡️ Apple Music. Kindly sign in with your Apple Music account to continue",
      showCloseButton: true,
      confirmButtonText: "SIGN IN."
    });
    if (result.value) {
      await MusicKit.getInstance().authorize();
    }
    return;
  }
  try {
    const response = await fetch("/playlist", {
      method: "POST",
      body: JSON.stringify({
        playlist: url,
        platform: getDestinationPlatform(url)
      }),
      headers: {
        "Content-Type": "application/json",
        "Music-User-Token": `${MusicKit.getInstance().musicUserToken}`
      }
    });
    raiseForStatus(response);
    let { task_id } = await response.json();
    const progressUrl = `/celery-progress/${task_id}/`;
    CeleryProgressBar.initProgressBar(progressUrl);
  } catch (error) {
    CeleryProgressBar.onErrorDefault();
  }
};
