FROM python:3

# Copy app in
COPY . . 
RUN pip3 install -r requirements.txt
CMD python main.py
