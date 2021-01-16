# set base image (host OS)
FROM python:3.8

# set the working directory in the container
WORKDIR /bot

RUN apt-get update ##[edited]
RUN apt-get install ffmpeg libsm6 libxext6 -y

# copy the dependencies file to the working directory
COPY requirements.txt ./
# install dependencies
RUN pip install --no-cache-dir -r requirements.txt
# copy the content of the local src directory to the working directory
COPY bot/ .

CMD [ "python", "./bot.py" ]
