# UroLogic

UroLogic is a student project that demonstrates urine-strip screening rules, data structures, and discrete mathematics. It is a teaching simulation, not a diagnostic tool.

## Run locally

```bash
python -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

Streamlit prints a local address and a network address when available. Data is held in the current Streamlit session and is not a permanent medical record.

## Publish a shareable website

1. Push this project to a GitHub repository.
2. Sign in to [Streamlit Community Cloud](https://share.streamlit.io/) with GitHub and choose **Create app**.
3. Select the repository and branch, set the main file path to `streamlit_app.py`, and deploy.
4. Streamlit Community Cloud will provide a public `*.streamlit.app` URL that you can open from anywhere.

The current folder is the app source; a public URL is created only after it is deployed through a hosting account.
