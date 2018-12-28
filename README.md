## Playlistor
self-hosted apple music to spotify playlist convertor

## Demo

![Demo](docs/demo.png)

## Installing
This assumes you have python 3.6 or higher, [foreman](https://www.npmjs.com/package/foreman) and [redis](https://redis.io/topics/quickstart) installed.
Clone repository or download zip and extract. Open terminal and navigate to `playlistor`. Run the following commands to create virtual environment and install dependencies.

* `python3 -m"venv" env && . env/bin/activate`
* `pip3 install -r requirements.txt`

Before starting the app, copy `env.sample` to `.env`, set all the required environmental variables in the `.env` file and have redis running in another terminal.
You can now run the app with `nf start --port 8000`.


## Usage
To use app, you'll first have to login `localhost:8000/login` with your spotify account credentials. After successful authentication, you'll be redirected to main page. On the main page, enter an apple music playlist and click submit.

## TODO
- [ ] Add feature to convert apple music playlist to spotify
