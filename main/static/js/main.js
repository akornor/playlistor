const COOKIE_NAME = 'newsletter-modal'

window.onload = function(event){
  if (!document.cookie.includes(COOKIE_NAME)){
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
          return response.json();
        }catch(e){
          Swal.showValidationMessage(
            `Request failed: ${e}`
          )
        }
      },
      allowOutsideClick: () => !Swal.isLoading()
    }).then((result) => {
      // set cookie
      document.cookie = `${COOKIE_NAME}=1; max-age=604800; path=/`

      if (result.value.email) {
        Swal.fire({
          title: 'Thank you for joining our newsletter.',
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
    const { playlist_url, destination, missed_tracks, number_of_tracks } = result;
    progressBarElement.style.backgroundColor = "#76ce60";
    // reset messaging elements
     $("#matched-tracks-info")?.remove()
     progressBarMessageElement.innerHTML = ''
    if (playlist_url){
      progressBarMessageElement.innerHTML = `<a target="_blank" href="${playlist_url}">${playlist_url}</a>`

      // Extract into functions to be cleaner.
      const clipboardButton = document.createElement('button');
      clipboardButton.innerHTML = "Copy to clipboard"
      clipboardButton.setAttribute('class', 'clipboard-btn');
      clipboardButton.setAttribute('data-clipboard-text', playlist_url)
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
    }else if (!playlist_url && destination === 'apple-music'){
      progressBarMessageElement.innerHTML = 'Check your recently created playlists on Apple Music.';
    }

    if (missed_tracks && number_of_tracks) {
      const matchedTracksInfo = document.createElement('span')
      matchedTracksInfo.setAttribute('id', 'matched-tracks-info')
      matchedTracksInfo.style.fontSize = '0.9em'
      matchedTracksInfo.style.fontStyle = 'italic'
      matchedTracksInfo.style.paddingBottom = '10px'
      matchedTracksInfo.innerHTML = `Successfully matched ${ missed_tracks.length === 0 ? 'all' : number_of_tracks - missed_tracks.length + ' out of ' + number_of_tracks} tracks on playlist.`
      const oldMatchedTracksInfo = document.getElementById('matched-tracks-info')
      if (oldMatchedTracksInfo) {
        progressBarElement.removeChild(oldMatchedTracksInfo)
      }
      progressBarElement.appendChild(matchedTracksInfo)
    }

    resetButton();
  }

async function onError(progressBarElement, progressBarMessageElement, excMessage) {
    progressBarElement.style.backgroundColor = "#dc4f63";
    $("#matched-tracks-info")?.remove()
    progressBarMessageElement.innerHTML = ''
    if (excMessage.includes('404')) {
      progressBarMessageElement.innerHTML = "Playlist not found! It's likely playlist is private."
    } else if(excMessage.includes('403') && MusicKit.getInstance().isAuthorized) {
      try{
        await MusicKit.getInstance().storekit._reset()
        progressBarMessageElement.innerHTML = "Something went wrong. Please try again :)"
      }catch(e) {
        console.log(e)
      }
    } else {
      progressBarMessageElement.innerHTML = "Uh-Oh, something went wrong! DM <a href='twitter.com/playlistor_io'>@playlistor_io</a> on Twitter or email <a href='mailto:playlistor.io@gmail.com'>playlistor.io@gmail.com</a> for support.";
    }
    resetButton();
  }

function onRetry(progressBarElement, progressBarMessageElement, excMessage, retryWhen) {
    retryWhen = new Date(retryWhen);
    let message = 'Retrying in ' + Math.round((retryWhen.getTime() - Date.now())/1000) + 's';
    progressBarElement.style.backgroundColor = "#dc4f63";
    $("#matched-tracks-info")?.remove()
    progressBarMessageElement.innerHTML = ''
    progressBarMessageElement.innerHTML = `Uh-Oh, something went wrong! ${message}`;
  }

function onProgress(
    progressBarElement,
    progressBarMessageElement,
    progress
  ) {
    $("#matched-tracks-info")?.remove()
    progressBarMessageElement.innerHTML = ''
    progressBarElement.style.backgroundColor = "#68a9ef";
    progressBarElement.style.width = progress.percent + "%";
    progressBarMessageElement.innerHTML =
      progress.current + " of " + progress.total + " songs processed.";
  }

async function onTaskError(progressBarElement, progressBarMessageElement, excMessage) {
        progressBarElement.style.backgroundColor = "#dc4f63";
        excMessage = excMessage || '';
        $("#matched-tracks-info")?.remove()
        progressBarMessageElement.innerHTML = ''
        if (excMessage.includes('404')) {
          progressBarMessageElement.innerHTML = "Playlist not found! It's likely playlist is private 🔒."
        } else if (excMessage.includes('403') && MusicKit.getInstance().isAuthorized) {
          try{
            await MusicKit.getInstance().storekit._reset()
            progressBarMessageElement.innerHTML = "Something went wrong. Please try again :)"
          }catch(e) {
            console.log(e)
          }
        }
        else {
          progressBarMessageElement.innerHTML = "Uh-Oh, something went wrong! DM <a href='twitter.com/playlistor_io'>@playlistor_io</a> on Twitter or email <a href='mailto:playlistor.io@gmail.com'>playlistor.io@gmail.com</a> for support.";
        }
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
  const invertOrder = document.getElementById("invert_order").checked;
  event.preventDefault();
  const musicKit = MusicKit.getInstance();
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
  if (isSpotifyPlaylistURL(url) && musicKit.isAuthorized){
    let lastLoginDate = await localStorage.getItem("LAST_APPLE_MUSIC_LOGIN");
    const today = new Date()
    const MONTH_THRESHOLD = 1
    if (!lastLoginDate || (monthDiff(new Date(lastLoginDate), today) > MONTH_THRESHOLD)){
      try{
        await musicKit.storekit.renewUserToken();
        await localStorage.setItem("LAST_APPLE_MUSIC_LOGIN", new Date().toISOString());
      }catch(e){
        console.log(e)
        // reset persisted apple music credentials.
        await musicKit.storekit._reset()
      }
    }
  }
  if (
    isSpotifyPlaylistURL(url) &&
    !musicKit.isAuthorized
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
      await musicKit.authorize();
      await localStorage.setItem("LAST_APPLE_MUSIC_LOGIN", new Date().toISOString())
    }
    return;
  }
  try {
    const response = await fetch("/playlist", {
      method: "POST",
      body: JSON.stringify({
        playlist: url,
        platform: getDestinationPlatform(url),
        invert_order: invertOrder
      }),
      headers: {
        "Content-Type": "application/json",
        "Music-User-Token": `${musicKit.musicUserToken}`
      }
    });
    raiseForStatus(response);
    const { task_id } = await response.json();
    const progressUrl = `/celery-progress/${task_id}/`;
    CeleryProgressBar.initProgressBar(progressUrl, {onProgress, onError, onSuccess, onTaskError, onRetry});
  } catch (error) {
    const progressBarElement = $("#progress-bar")
    const progressBarMessageElement = $("#progress-bar-message")
    onError(progressBarElement, progressBarMessageElement)
  }
};
