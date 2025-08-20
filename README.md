# LinkedInSearch

Simple Tool for employees recon (searching trere LinkedIn profile)

1) Create free account in : https://serper.dev (you can use Temp mail https://temp-mail.org/)
2) Take the API Key and export it on Linux machine:
```bash
export SERPER_API_KEY="XXXXXXXXX"
```
3) Create enviroment
```bash
python3 -m venv LinkedInSearch
```
4) Enter the enviroment
```bash
Source LinkedInSearch/bin/active
```
5) Install:
```bash
requests
```
6) Usage:
```python
python3 LinkedInSearch.py -q "Company" --pages 5 --per-page 20
```
