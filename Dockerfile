FROM python:3

##### CONFIGURATION FOR PULLING PRIVATE REPO ######
RUN mkdir /root/.ssh
# Copy deploy key as SSH key. Note that this key is a read-only deploy key
# specifically created for the common repo. It is copied from that repo and
# shared amongst repos that need it.
ADD common_deploy_key /root/.ssh/id_rsa
RUN chmod 700 /root/.ssh/id_rsa && chown -R root:root /root/.ssh
# Create known_hosts
RUN touch /root/.ssh/known_hosts
# Add github key. Otherwise, "Host key verification failed. "
RUN ssh-keyscan github.com >> /root/.ssh/known_hosts
##### END PRIVATE REPO CONFIG #####################

# Copy app in
COPY . . 
RUN pip3 install -r requirements.txt
# App runs on port 5000.
EXPOSE 5000
# TODO: -w4 and other gunicorn configuration settings...
CMD gunicorn "main:main_gunicorn()" -b 0.0.0.0:5000
#CMD python main.py
