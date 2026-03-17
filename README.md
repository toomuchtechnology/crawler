It's an asynchronous web crawler built on FastAPI, BeautifulSoup and Docling which saves parsed pages in Markdown and uses Valkey to save associated page and image URLs (*md_file_name: page_url*, *page_url: image_url*).

**Docker installation**:
1. env: ```VALKEY_HOST=valkey```
2. ```docker compose build --progress:plain``` for logging.
3. ```docker compose up```

Use ```docker compose start``` and ```docker compose stop``` to start and stop the project.



**Local installation**:
1. .env: ```VALKEY_HOST=localhost```
2. Activate venv (preferably).
3. Install the desired version of ```torch``` and ```torchvision``` from [https://pytorch.org/get-started/locally/]().
4. Install the libraries from ```requirements.txt```.
5. ```docker run -p 6379:6379 valkey/valkey```
6. ```uvicorn main.app --host 0.0.0.0 --port 8000```



Get all endpoints by going to [localhost:8000/docs]().