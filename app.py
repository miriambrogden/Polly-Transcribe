# Written by Miriam Snow
# March 27, 2020
import logging
import boto3
import os
from boto3 import Session
from botocore.exceptions import BotoCoreError, ClientError
from contextlib import closing
from datetime import date
import sys
import uuid
import subprocess
from tempfile import gettempdir
import time
import json

bucketName = "pollytranscribeapp"
option = ""
accent = "Joanna"
accentArray = ["Nicole", "Russell", "Amy", "Brian", "Joanna", "Joey"]


def upload_objects(bucket):
    s3 = boto3.client('s3')
    with open(output, "rb") as f:
        s3.upload_fileobj(f, bucket, uploadFileName)
        
def get_files(bucketName, array, ext):
    s3 = boto3.resource('s3')
    for bucket in s3.buckets.all():
        if (bucket.name == bucketName):
            for key in bucket.objects.all():
                chosenfilename = key.key
                extension = chosenfilename.split(".")
                if (extension[1] == ext):
                    array.append(chosenfilename)
                    
def get_all_files(bucketName, array):
    s3 = boto3.resource('s3')
    for bucket in s3.buckets.all():
        if (bucket.name == bucketName):
            for key in bucket.objects.all():
                array.append(key.key)
                

while (option != "7"):
    
    textFilesArray = []
    audioFilesArray = []
    allFilesArray = []
    
    get_files(bucketName, textFilesArray, "txt")
    get_files(bucketName, audioFilesArray, "mp3")
    get_all_files(bucketName, allFilesArray)
    
    count = 0
    
    print("\n")
    print("What would you like to do?")
    print("1 - Text to speech (polly)")
    print("2 - Speech to text (transcribe)")
    print("3 - Change accent")
    print("4 - Download a file")
    print("5 - Upload a file")
    print("6 - Delete a file")
    print("7 - Quit")
    option = input("Please type a number: ")
    
    #POLLY (text to speech)
    if (option == "1"):
        
        print("\n")
        print("What file would you like to convert to audio?")
        for p in textFilesArray:
            print(str(count + 1) + " - " + p)
            count = count + 1
        fileNumber = input("Please type a number: ")
        index = int(fileNumber) - 1
        textFile = textFilesArray[index]
        
        #download text file to local directory
        s3 = boto3.client('s3')
        s3.download_file(bucketName, textFile, textFile)
        textFileObj = open(textFile, "r")
        
        # get file contents and load into a string
        textstring = ""
        for line in textFileObj:
            textstring = textstring + " " + line
            
        # convert text to speech
        session = Session(profile_name="MSnow")
        polly = session.client("polly")

        try:
            response = polly.synthesize_speech(Text=textstring, OutputFormat="mp3", VoiceId=accent)
        except (BotoCoreError, ClientError) as error:
            print(error)
            sys.exit(-1)

        if "AudioStream" in response:
            with closing(response["AudioStream"]) as stream:
                output = "speech.mp3"
                try:
                    with open(output, "wb") as file:
                        file.write(stream.read())
                except IOError as error:
                    print(error)
                    sys.exit(-1)
        else:
            print("Could not stream audio")
            sys.exit(-1)
    
        # upload audio file to s3 bucket
        temp = textFile[:-4]
        uploadFileName = temp + ".mp3"
        upload_objects(bucketName)
        
        #remove temp files
        os.system("rm speech.mp3")
        
        print(uploadFileName + " created and uploaded to the cloud")
        
    # transcribe (speech to text)
    if (option == "2"):

        print("\n")
        print("What file would you like to convert to text?")
        for m in audioFilesArray:
            print(str(count + 1) + " - " + m)
            count = count + 1
        fileNumber1 = input("Please type a number: ")
        index1 = int(fileNumber1) - 1
        myAudio = audioFilesArray[index1]

        myAudioFile = myAudio.replace(" ", "+")
        myTextFile = myAudio.replace(".mp3", ".txt")
        s3 = boto3.client('s3', region_name='ca-central-1')
        transcribe = boto3.client('transcribe')
        job_name = str(uuid.uuid1())
        url = "https://pollytranscribeapp.s3.amazonaws.com/"
        job_uri = url + myAudioFile
        
        #Start transcription job using the test mp3 file located in a s3 bucket. Stores the transcription in the same bucket
        transcribe.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={'MediaFileUri': job_uri},
            MediaFormat='mp3',
            OutputBucketName=bucketName,
            LanguageCode='en-US'
        )
        
        #Get transcription job
        while True:
            status = transcribe.get_transcription_job(TranscriptionJobName=job_name)
            if status['TranscriptionJob']['TranscriptionJobStatus'] in ['COMPLETED', 'FAILED']:
                break;
                
        #get information from json file
        transcriptionFile = job_name + ".json"
        result = s3.get_object(Bucket=bucketName, Key=transcriptionFile)
        data = json.load(result['Body'])
        transcriptText = data['results']['transcripts']
        myText = transcriptText[0]['transcript']
        
        #create text file in local directory
        myTextFileObj = open(myTextFile,"w+")
        myTextFileObj.write(myText)
        myTextFileObj.close()

        #upload file from local directory
        s3 = boto3.client('s3')
        with open(myTextFile, "rb") as f:
            s3.upload_fileobj(f, bucketName, myTextFile)

        #delete all temporary file
        s3 = boto3.resource('s3')
        s3.Object(bucketName, transcriptionFile).delete()
        s3.Object(bucketName, ".write_access_check_file.temp").delete()
        os.system("rm " + myTextFile)
        
        print(myTextFile + " created and uploaded to the cloud")
        
        
    # change accent
    if (option == "3"):
        print("\n")
        print("What accent would you like to use?")
        print("1 - Nicole (australian female)")
        print("2 - Russell (australian male)")
        print("3 - Amy (british female)")
        print("4 - Brian (british male)")
        print("5 - Joanna (american female)")
        print("6 - Joey (american male)")
        accentIndex = input("Please type a number: ")
        
        accent = accentArray[int(accentIndex) -1]
        print("Accent changed to " + accent)
        
    #download file
    if (option == "4"):        
        print("\n")
        print("What file would you like to download?")
        for k in allFilesArray:
            print(str(count + 1) + " - " + k)
            count = count + 1
        fileNumber = input("Please type a number: ")
        index = int(fileNumber) - 1
        allFile = allFilesArray[index]
        
        #download file to local directory
        s3 = boto3.client('s3')
        s3.download_file(bucketName, allFile, allFile)
        
        print(allFile + " downloaded to local directory")
        
    #upload file
    if (option == "5"):
        print("\n")
        myFile = input("Please input the name of your file to upload: ")
        s3 = boto3.client('s3')
        with open(myFile, "rb") as f:
            s3.upload_fileobj(f, bucketName, myFile)
            
        print(myFile + " uploaded to the cloud")
        
    if (option == "6"):        
        print("\n")
        print("What file would you like to delete?")
        for l in allFilesArray:
            print(str(count + 1) + " - " + l)
            count = count + 1
        fileNumber2 = input("Please type a number: ")
        index2 = int(fileNumber2) - 1
        allFile2 = allFilesArray[index2]
        
        #delete file from s3 bucket
        s3 = boto3.resource('s3')
        s3.Object(bucketName, allFile2).delete()
        
        print(allFile2 + " deleted from the cloud")
        

