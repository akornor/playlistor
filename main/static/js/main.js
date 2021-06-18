window.onload = function(event){
  if (true && !localStorage.getItem("subscribed")){
      Swal.fire({
      title: 'Be the first to know',
      html:  `<p>Hi, I’m actively working on a new and improved version of <a href="/" style="color:#3085d6">Playlistor</a> with <b>exciting features</b> I can’t wait to share.
      Be the first to know when it goes live 🚀<br/>-- <a href="https://twitter.com/raymxnde" style="color:#3085d6">Raymond Akornor(@raymxnde)</a></p>`,
      input: 'email',
      inputAttributes: {
        autocapitalize: 'off',
        placeholder: 'Enter your email address'
      },
      showCloseButton: true,
      confirmButtonText: 'Submit',
      showLoaderOnConfirm: true,
      preConfirm: async (email) => {
        try{
          const response = await fetch("/subscribers", {
            method: "POST",
            body: JSON.stringify({
              email,
            }),
            headers: {
              "Content-Type": "application/json",
            }
          });
          if (!response.ok) {
            throw new Error(response.statusText)
          }
          // set flag to indicate user has subscribed to newsletter
          localStorage.setItem("subscribed", true)
          return response.json();
        }catch(e){
          Swal.showValidationMessage(
            `Request failed: ${e}`
          )
        }
      },
      allowOutsideClick: () => !Swal.isLoading()
    }).then((result) => {
      if (result.value.email) {
        Swal.fire({
          title: 'Thanks for joining our newsletter.',
        })
      }
    })
  }
}

const $ = (window.$ = document.querySelector.bind(document));

let button = $("#submit_btn");

function onSuccess(
    progressBarElement,
    progressBarMessageElement,
    result
  ) {
    progressBarElement.style.backgroundColor = "#76ce60";
    progressBarMessageElement.innerHTML = is_valid_url(result)
      ? `<a target="_blank" href="${result}">${result}</a>`
      : result;
    // Extract into functions to be cleaner.
    const clipboardButton = document.createElement('button');
    clipboardButton.innerHTML = "Copy to clipboard"
    clipboardButton.setAttribute('class', 'clipboard-btn');
    clipboardButton.setAttribute('data-clipboard-text', result)
    new ClipboardJS('.clipboard-btn');
    const i = document.createElement('i');
    i.setAttribute('class', 'fas fa-clipboard-list');
    clipboardButton.appendChild(i);
    progressBarMessageElement.appendChild(clipboardButton);
    const spanEl = document.createElement('span');
    spanEl.setAttribute('class', 'tooltiptext');
    spanEl.innerHTML = "Copied!"
    clipboardButton.appendChild(spanEl)
    clipboardButton.onclick = function(event){
      const tooltip = document.querySelectorAll('.tooltiptext')[0];
      tooltip.style.visibility = 'visible';
      setTimeout(function() {
        tooltip.style.visibility = 'hidden';
      }, 1000);
    }
    resetButton();
  }

function onError(progressBarElement, progressBarMessageElement) {
    progressBarElement.style.backgroundColor = "#dc4f63";
    progressBarMessageElement.innerHTML = "Uh-Oh, something went wrong!";
    resetButton();
  }

function onRetry(progressBarElement, progressBarMessageElement, excMessage, retryWhen) {
    retryWhen = new Date(retryWhen);
    let message = 'Retrying in ' + Math.round((retryWhen.getTime() - Date.now())/1000) + 's';
    progressBarElement.style.backgroundColor = "#dc4f63";
    progressBarMessageElement.innerHTML = `Uh-Oh, something went wrong! ${message}`;
  }

function onProgress(
    progressBarElement,
    progressBarMessageElement,
    progress
  ) {
    progressBarElement.style.backgroundColor = "#68a9ef";
    progressBarElement.style.width = progress.percent + "%";
    progressBarMessageElement.innerHTML =
      progress.current + " of " + progress.total + " songs processed.";
  }

function onTaskError(progressBarElement, progressBarMessageElement, excMessage) {
        progressBarElement.style.backgroundColor = this.barColors.error;
        excMessage = excMessage || '';
        progressBarMessageElement.textContent = "Uh-Oh, something went wrong!"
        resetButton();
    }

const SPOTIFY_PLAYLIST_URL_REGEX = /^http(s):\/\/open\.spotify\.com\/(user\/.+\/)?playlist\/.+$/;
const APPLE_MUSIC_PLAYLIST_URL_REGEX = /^http(s):\/\/(embed.)?music\.apple\.com\/.{2}\/playlist\/.+$/;

const is_valid_url = str => {
  const regexp = /^(?:(?:https?):\/\/)?(?:(?!(?:10|127)(?:\.\d{1,3}){3})(?!(?:169\.254|192\.168)(?:\.\d{1,3}){2})(?!172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2})(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5])){2}(?:\.(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-4]))|(?:(?:[a-z\u00a1-\uffff0-9]-*)*[a-z\u00a1-\uffff0-9]+)(?:\.(?:[a-z\u00a1-\uffff0-9]-*)*[a-z\u00a1-\uffff0-9]+)*(?:\.(?:[a-z\u00a1-\uffff]{2,})))(?::\d{2,5})?(?:\/\S*)?$/;
  return regexp.test(str);
};

// copied from https://stackoverflow.com/questions/2536379/difference-in-months-between-two-dates-in-javascript
function monthDiff(d1, d2) {
    var months;
    months = (d2.getFullYear() - d1.getFullYear()) * 12;
    months -= d1.getMonth();
    months += d2.getMonth();
    return months <= 0 ? 0 : months;
}

function isSpotifyPlaylistURL(url){
  return SPOTIFY_PLAYLIST_URL_REGEX.test(url)
}

function isAppleMusicPlaylistURL(url){
  return APPLE_MUSIC_PLAYLIST_URL_REGEX.test(url)
}

function isSupportedPlaylistURL(url){
  return isSpotifyPlaylistURL(url) || isAppleMusicPlaylistURL(url)
}


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
  if (isSpotifyPlaylistURL(url)) {
    return "apple-music";
  } else if (isAppleMusicPlaylistURL(url)) {
    return "spotify";
  } else {
    throw new Error("Platform not yet supported.");
  }
}

async function maybeExpandURL(url) {
  if (isSupportedPlaylistURL(url)) {
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
  const playlist = $("#input_big").value.trim();
  if (playlist === "") {
    return;
  }
  if (!is_valid_url(playlist)) {
    Swal.fire(
      "Invalid URL",
      "Enter valid playlist url e.g https://itunes.apple.com/us/playlist/ep-3-paak-house-radio-playlist/pl.be45d23328f642cc91cf7086c7126daf or https://open.spotify.com/playlist/0uvKonJpIZpRWoffhkMq2O"
    );
    return;
  }
  const url = await maybeExpandURL(playlist);
  if (!isSupportedPlaylistURL(url)){
    // TODO: Extract into function.
    Swal.fire(
      "Invalid URL",
      "Enter valid playlist url e.g https://itunes.apple.com/us/playlist/ep-3-paak-house-radio-playlist/pl.be45d23328f642cc91cf7086c7126daf or https://open.spotify.com/playlist/0uvKonJpIZpRWoffhkMq2O"
    );
    return;
  }
  displaySpinner();
  if (isSpotifyPlaylistURL(url) && MusicKit.getInstance().isAuthorized){
    let lastLoginDate = await localStorage.getItem("LAST_APPLE_MUSIC_LOGIN");
    if (!lastLoginDate){
      try{
        await MusicKit.getInstance().storekit.renewUserToken();
        await localStorage.setItem("LAST_APPLE_MUSIC_LOGIN", new Date.toISOString());
      }catch(e){
        // do nothing
        console.log(e)
      }
    }else{
      lastLoginDate = new Date(lastLoginDate);
      const today = new Date();
      const MONTH_THRESHOLD = 1
      if (monthDiff(lastLoginDate, today) > MONTH_THRESHOLD){
        try{
          await MusicKit.getInstance().storekit.renewUserToken();
          await localStorage.setItem("LAST_APPLE_MUSIC_LOGIN", new Date.toISOString());
        }catch(e){
          // do nothing
          console.log(e)
        }
      }
    }
  }
  if (
    isSpotifyPlaylistURL(url) &&
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
      await localStorage.setItem("LAST_APPLE_MUSIC_LOGIN", new Date().toISOString())
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
    CeleryProgressBar.initProgressBar(progressUrl, {onProgress, onError, onSuccess, onTaskError, onRetry});
  } catch (error) {
    CeleryProgressBar.onErrorDefault();
  }
};
