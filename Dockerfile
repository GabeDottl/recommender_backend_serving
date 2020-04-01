FROM python:3

# Copy app in
COPY . . 
RUN pip3 install -r requirements.txt

# App runs on port 5000.
EXPOSE 5000
CMD python main.py
