It's an asynchronous web crawler built on BeautifulSoup and Docling which saves parsed pages in Markdown.

Launch like this:
```
uvicorn main:app --reload
```

It runs on port 8000 and requires Valkey running on port 6379.

Get all endpoints by going to localhost:8000/docs.