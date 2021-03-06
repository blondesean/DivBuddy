# \/\/ --- Change Inputs --- \/\/

#File save location 
source_symbols = "/Users/SeanDuncan/Desktop/Professional/Stock Monitor Data/Lists/S&P500_12_3_17.csv" #https://datahub.io/core/s-and-p-500-companies
fileLocation = "/Users/SeanDuncan/Desktop/Professional/Stock Monitor Data/Runs/Phase_2/"

#How many symbols should we pull
pullLimit = 50
loops = 1

#Time between runs, no negatives
dayDelay = 1
hourDelay = 0
minuteDelay = 0
secondDelay = 0
secondRunOffset = 0 #in hours
delayRequests = 1

#Market Parameters
averageReturnForMarket = .09

#Addressing
sendMail = 1
From = "seanwithwings@gmail.com"
To = "jesse226@gmail.com"
CC = "svd5148@gmail.com"
Password = "XXXX"

# /\/\ --- Change Inputs --- /\/\

#import libraries
import csv
import urllib2
import pandas as pd
import time
import thread
import numpy as np
from email.mime.multipart import MIMEMultipart
from email import encoders
from email.message import Message
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
import smtplib
import mimetypes
import os
import sys
from datetime import datetime
from datetime import date
import threading
from bs4 import BeautifulSoup  
from lxml import html
import requests

#Formats the attachment fed into the 
def prep_attachment(file):
        ctype, encoding = mimetypes.guess_type(file)
        if ctype is None or encoding is not None:
            ctype = "application/octet-stream"

        maintype, subtype = ctype.split("/", 1)

        if maintype == "text":
            fp = open(file)
            # Note: we should handle calculating the charset
            attachment = MIMEText(fp.read(), _subtype=subtype)
            fp.close()
        elif maintype == "image":
            fp = open(file, "rb")
            attachment = MIMEImage(fp.read(), _subtype=subtype)
            fp.close()
        elif maintype == "audio":
            fp = open(file, "rb")
            attachment = MIMEAudio(fp.read(), _subtype=subtype)
            fp.close()
        else:
            fp = open(file, "rb")
            attachment = MIMEBase(maintype, subtype)
            attachment.set_payload(fp.read())
            fp.close()
            encoders.encode_base64(attachment)

        #Format attachment and return
        attachment.add_header("Content-Disposition", "attachment", filename=os.path.basename(file))
        return attachment

#The Body message 
def body(delays, maxRuns, maxComps, onRun):
    html =      "<html>\
                  <head></head>\
                  <body>\
                    <p>Good Afternoon " + "Jesse" + ",</p>\
                    <p>The formula has been run on the S&P 500 for today. See attached.</p>\
                    <p>This script is on run " + str(onRun) + " of " + str(maxRuns) + " and it runs every " + str(delays[0]) + " day(s), " + str(delays[1]) + " hour(s), " + str(delays[2]) + " minute(s) and " + str(delays[3]) + " seconds.</p>\
                    <p>The script pulled " + str(maxComps) + " companies to monitor. </p> \
                    <p>Thank you,<br />" + "Sean" + "</p> \
                  </body>\
                </html>"
    return html

#Create the CSV
def monitor_market_file(source, pullCount, saveLocation, date):
  #Get the stock values of interest
  symbols = pd.read_csv(source)

  #Set Column Headers for data frame, first row of data
  data = np.array([\
    # 0,1,2,3,4
    ["Symbol", "Name", "Sector", "Div_Per_Share", "Earnings_Per_Share",\
    #5,6,7,8,9
     "PE_Ratio", "Last_Trade_Price", "Dividend_Yield", "Risk_Free_10_Years", "Beta",\
    #10,11,12,13,14
     "Average_Return_for_Market", "Dividend_Growth_Rate", "Earnings_Growth", "F_Div_Yield", "Required_Rate_of_Return",\
    #15,16,17, 18
     "Calculated_Value", "Value_Differential", "Calculated_Move", "Problem"]])

  #Scrape risk free 10 year rate since every company uses it
  riskFreeRate10Years = getRiskFree10()

  #Grab the symbol data and append to the csv
  for i, row in symbols.iterrows():
      if i <= (pullCount - 1):

        #Start pulling data for this company iterations
        compSymbol = row['Symbol']
        #compSymbol = "AAPL"
        print("Company #" + str(i + 1) + " - Pulling data for symbol: " + compSymbol)

        #Strip the outside brackets, seek additional scraped info, calculated columns
        comp_stats = np.array([[\
          #Stock symbol information
          row['Symbol'],row['Name'],row['Sector'],\
          #Remaining info we have to grab
          0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]], dtype = "|S75") #string length of 75

        #Dividens per share, dividen growth rate
        comp_stats[0][3], comp_stats[0][11] = getDividendGrowth(compSymbol)
        
        #Earnings per share, EPS growth rate
        comp_stats[0][4], comp_stats[0][12] = getEPSGrowthRate(compSymbol)

        # PE, last close price, forward div yield
        comp_stats[0][5], comp_stats[0][6], comp_stats[0][13] = getPE_lastClose(compSymbol)

        #Global Variables
        print("    Requesting general stock info")
        comp_stats[0][8] = riskFreeRate10Years
        comp_stats[0][9] = getBeta(compSymbol)  #Symbol Data from yahoo (was)
        comp_stats[0][10] = averageReturnForMarket

        #Declare Vars for easier understanding
        C = float(comp_stats[0][8]) #risk free rate 10 years
        D = float(comp_stats[0][9]) #beta
        E = float(comp_stats[0][10]) #average return for market
        F = float(comp_stats[0][11]) #div growth rate
        G = float(comp_stats[0][12]) #eps growth
        H = (float(comp_stats[0][3]) if comp_stats[0][3] != "N/A" else 0) #div per share
        I = (float(comp_stats[0][4]) if comp_stats[0][4] != "N/A" else 0) #eps 
        J = (float(comp_stats[0][5]) if comp_stats[0][5] != "N/A" else 0) #pe ratio
        L = (float(comp_stats[0][6]) if comp_stats[0][6] != "N/A" else 0) #last_trade_price

        #Intermediary calculations
        comp_stats[0][14] = (C + D * (E - C)) #Required_Rate_of_Return 

        #Declare Vars for easier understanding
        B = float(comp_stats[0][14])

        #Big calculations, make decisions
        comp_stats[0][15] = ((H / (1+B)) + \
           (H * ((1+F) ** 2) / ((1+B)**2)) + \
           (H * ((1+F) ** 3) / ((1+B)**3)) + \
           (I * ((1+G) ** 3) * J / (1+B) ** 3 )) #Calculated value 
        
        #Declare Vars for easier understanding
        Z = round(float(comp_stats[0][15]),8)
        
        #Store final calculated value
        comp_stats[0][16] = Z - L #Value_Differential \ 

        #If value > 0 then worth buying
        if ((Z - L) > 0 ):
          comp_stats[0][17] = "Yes" #Calculated_Move 
        else:
          comp_stats[0][17] = "No" #Calculated_Move 
        
        #Problem checks 
        problems = ""
        if (comp_stats[0][3] == "N/A"):
          problems = problems + "No Div Per Share, "
        if (comp_stats[0][4] == "N/A"):
          problems = problems + "No EPS, "
        if (comp_stats[0][5] == "N/A"):
          problems = problems + "No PE, "
        if (comp_stats[0][6] == "N/A"):
          problems = problems + "No Last Trade Price, "
        if (comp_stats[0][9] == "N/A"):
          problems = problems + "No Beta, "
        if (comp_stats[0][11] == "N/A"):
          problems = problems + "No Dividends, "
          comp_stats[0][11] = 0 #No dividends is possible, will have 0 div growth rate in model
        if (comp_stats[0][12] == "N/A"):
          problems = problems + "No EPS Growth, "
        if (comp_stats[0][14] == "N/A"):
          problems = problems + "No F Div Yield Growth, "
        if (problems == ""):
          problems = problems + "None"
        else:
          problems = problems[:-2]
        #Add list of problems if any
        comp_stats[0][18] = problems

        #Append each list of data to our existing file
        data = np.concatenate((data,comp_stats))
        print("    Resting for API request limit")

        #Rest time to make sure we are not booted for API request call limits
        time.sleep(delayRequests)

  #Write the dataframe to a csv
  print(saveLocation + 'test_' + str(date) + '.csv')
  with open(saveLocation + '/test_' + str(date) + '.csv', 'w') as csvfile:
    file = csv.writer(csvfile, delimiter = ',')
    file.writerows(data)

#Checks for values that are not valid numbers
def isVal(value):
  print("is " + str(value) + " a real value?")
  #Skip if we have a float
  if isinstance(value, float):
    try:
      #Check %
      if value.find("%"):
        value = value.replace("%", "")
      #Check Negatives
      if value.find("-"):
        value = float(value)
      #Check commas
      if value.find(","):
        value = value.replace(",","")
      #Check other
        value = float(value * 1)
    except ValueError:
      value = "N/A"
    except IndexError:
      value = "N/A"

  return value

def getDividendGrowth(ID):
  #Current date for unix second differential
  now = datetime.now()

  #End, current unix timestamp
  endCode = int(time.time())

  #Start, can only pull 6 years at a time 
  passedSeconds = date(now.year, now.month, now.day) - date(now.year - 6, now.month, now.day)
  passedSeconds = int(passedSeconds.total_seconds())
  startCode = endCode - passedSeconds
  
  #The Dividend URL page
  url = "https://finance.yahoo.com/quote/" + ID + "/history?period1=" + str(startCode) + "&period2=" + str(endCode) + "&interval=1mo&filter=history&frequency=1mo"
  print("    Scraping historical dividends == from URL: " + url)
  r = requests.get(url)

  # Turn the HTML into a Beautiful Soup object, strip out items into list with dividend identifier
  soup = BeautifulSoup(r.text, 'lxml')
  table = soup.find_all(class_="Ta(c) Py(10px) Pstart(10px)")

  #Parse out the number values
  i = 0
  dividends = []
  dividendGrowths = []
  blankDivs = 0
  temp = -1 #negative so we don't clear the first check
  string = "Null" #similar to temp, start with non-number
  while (i < len(table)):
    #Protect from stock splits
    if ("Stock Split" not in str(table[i])):
      #Some parsing to get to the number using common tags
      string = str(table[i])
      string = string[string.find("strong data-reactid="):]
      string = string[string.find(">") + 1:]
      if (string.find("</strong>") >= 1): 
        string = float(string[:string.find("</strong>")])
        #Find growth rate quarterly, or however it is published
        dividends.extend([string])
        if (isVal(temp) and temp > 0 and isVal(string) and string != 0.0):
          dividendGrowths.extend([temp / string])

    #Store the value for the next iteration, don't store a non-numeric value
    if (isVal(string)):
      temp = string
    i += 1

  #Average growth rate to get our estimate, if no dividens then give 99 to filter out
  if (len(dividends) > 1):
    #Recent dividend
    recent_div = dividends[0] + dividends[1] + dividends[2] + dividends[3]

    #Annualize adjustment
    quartersPassed = passedSeconds / 60 / 60 / 24 / 91.31 #91 = days in quarter
    adjustMult = ( quartersPassed / float(len(table)) )
    divGrowth = (sum(dividendGrowths) / len(dividendGrowths) - 1) * 4 * adjustMult

    #Subtract 1 for growth > 1, 4 since assuming quarterly divs, x multiplier to inc for missed quarters
    return(isval(recent_div), isval(divGrowth))
  else:
    return "N/A", "N/A"

def getEPSGrowthRate(ID):
  #Check for class stocks, return 99 if no 
  if (ID.find(".") > 0):
    return (99, 99)

  #Grabs html tree, seaches for identifer of earnings table, grows next year est growth
  url = 'https://finance.yahoo.com/quote/' + ID + '/analysts?p=' + ID
  print("    Scraping EPS this year == from URL: " + url)
  page = requests.get(url)
  tree = html.fromstring(page.content)
  values = tree.xpath('//span[@class="Trsdu(0.3s) "]/text()')
  values2 = tree.xpath('//td[@class="Ta(end) Py(10px)"]/text()')
  checkValues = tree.xpath('//span/text()')

  #Check to see if the values were pulled, if too short then throws error to epsExists, no negative growth rates/ N/As / need a percentage
  try:
    epsExists = 1 if values[51] != 0 \
    and values2[16].find("-") == -1 \
    and str(values2[16].replace("%","")) != "N/A" \
    and float(str(values2[16].replace("%",""))*1) else 0
  except IndexError:
    epsExists = 0
  except ValueError:
    epsExists = 0

  #check to make sure value exists
  if (len(values) != 0 and epsExists == 1) and checkValues[101] == "EPS Actual":
    EPS = isVal(values[51]) + isVal(values[50]) + isVal(values[49]) + isVal(values[48])
    earningsGrowth = isVal(values2[16])/100
  else:
    EPS = 99
    earningsGrowth = 99

  #This is the next year growth rate
  return (isVal(EPS), isVal(earningsGrowth))

#https://finance.yahoo.com/quote/AAPL?p=AAPL
def getPE_lastClose(ID):
  #Grabs html tree, seaches for identifer of earnings table, grows next year est growth
  #Get the PE
  url = 'https://finance.yahoo.com/quote/' + ID + '?p=' + ID
  print("    Scraping PE, Last close price, Forward Dividend Yield == from URL: " + url)
  page = requests.get(url)
  tree = html.fromstring(page.content)
  values = tree.xpath('//span[@class="Trsdu(0.3s) "]/text()')
  values2 = tree.xpath('//td[@class="Ta(end) Fw(b) Lh(14px)"]/text()')

  #Somepages like BHI 
  if len(values) != 0 and isVal[0] != "N/A" and isVal[6] != "N/A":
    return (isVal(values[6]),isVal(values[0]), str(values2[2]))
  else:
    return (99,99,99)

def getRiskFree10():
  #Grabs html tree, seaches for identifer of earnings table, grows next year est growth
  url = 'https://www.bloomberg.com/quote/USGG10YR:IND'
  print("Scraping risk free 10 year rate == from URL: " + url)
  page = requests.get(url)
  tree = html.fromstring(page.content)
  values = tree.xpath("//div[@class='price']/text()")

  #check to make sure value exists
  riskfree10 = isVal(values[0])
  return (riskfree10)

def getBeta(ID):
  #Check for class stocks, return 99 if no 
  if (ID.find(".") > 0):
    return "N/A"

  #Grabs html tree, seaches for identifer of earnings table, grows next year est growth
  url = 'https://finance.google.com/finance?q=' + ID
  print("    Scraping beta value == from URL: " + url)
  page = requests.get(url)
  tree = html.fromstring(page.content)
  values = tree.xpath('//td[@class="val"]/text()')

  #check to make sure value exists
  if (len(values) == 0 or values[9] == "N/A" or values[9] == "-" or values[9] == ""):
    return "N/A"

  #Remove symbols 
  betaVal = isVal(values[9])
  if (betaVal != "N/A"):
    return(float(betaVal))
  else:
    return "N/A"

#Send the email
def sendEmail(emailTo, emailFrom, emailCC, password, saveLocation, date, runNumber):
  #Log in to the gmail server
  server = smtplib.SMTP('smtp.gmail.com:587')
  server.ehlo()
  server.starttls()
  server.login(emailFrom,password)

  #Constuct Email
  #Declare the email and fill out basic information
  msg = MIMEMultipart()
  msg["From"] = emailFrom 
  msg["To"] = emailTo
  msg["CC"] = emailCC
  msg["Subject"] = "Phase 1 Prototype: DB Stock Update " + str(date)
  msg.preamble = "Sent from Python, Uses MIME formatting standards"
  receiving = (emailTo + ", " + emailCC).split(', ')

  #Attachment 
  fileToSend = saveLocation + '/test_' + str(date) + '.csv'
  attachment = prep_attachment(fileToSend)
  msg.attach(attachment)

  #Add Email Footer
  html = body([dayDelay,hourDelay,minuteDelay,secondDelay], loops, pullLimit, runNumber)

  #Convert to MIME format
  htmlBody = MIMEText(html, 'html')

  #Attach the created text
  msg.attach(htmlBody)

  #Send Email
  server.sendmail(emailFrom, receiving, msg.as_string())
  print("--- TO: " + emailTo + " | CC: " + emailCC + " | FROM: " + emailFrom + " ---")

  #logout to end
  server.quit()

def mainPurpose(nextRun, runCount = 1):
  #State the time
  now = datetime.now()
  date = str(now.year) + "-" + str(now.month) + "-" + str(now.day)
  print("Today's date is : " + date)

  #Create file
  monitor_market_file(source_symbols, pullLimit, fileLocation, date)

  #Send Email
  if(sendMail == 1):
    sendEmail(To, From, CC, Password, fileLocation, date, runCount)

  #Start again
  scheduler(runCount, nextRun)
 
def overflowDelay(Now, SecondDelay, MinuteDelay, HourDelay):

  #Safety Check, prevent overflow in incrementer
  if (Now.second + SecondDelay >= 60):
    print("Waiting " + str(Now.second + SecondDelay - 58) + " seconds to prevent overflow.")
    time.sleep(Now.second + SecondDelay - 59)
  if (Now.minute + MinuteDelay >= 60):
    print("Waiting " + str(Now.minute + MinuteDelay - 58) + " minutes to prevent overflow.")
    time.sleep((Now.minute + MinuteDelay - 59) * 60)
  if (Now.hour + HourDelay >= 24):
    print("Waiting " + str(Now.hour + HourDelay - 23) + " hours to prevent overflow.")
    time.sleep((Now.hour + HourDelay - 23) * 60 * 24)
    
def scheduler(runNumber, prevRun):
  #Increment Counter 
  runNumber = runNumber + 1

  #Timer control - time until next run and function to run
  #Set up reoccurence process
  now = datetime.now()
  delta_t = prevRun - now
  secs = delta_t.seconds + 1
  next_date = prevRun.replace(day=prevRun.day+dayDelay, hour=prevRun.hour+hourDelay, minute=prevRun.minute+minuteDelay, second=prevRun.second+secondDelay, microsecond=prevRun.microsecond)

  #Safety Check, prevent overflow in incrementer
  overflowDelay(now, secondDelay, minuteDelay, hourDelay)

  #Print schedule and run
  if (runNumber <= loops):
    timer = threading.Timer(secs,mainPurpose,[next_date,runNumber])
    print("The time is " + str(now))
    print("Next run at " + str(prevRun) + " which is run #" + str(runNumber))
    print("In the hole " + str(next_date))
    timer.start()

# --- Start --- 
#The first run 
now = datetime.now()

#To adjust schedule to favorable time
if (now.hour+hourDelay+secondRunOffset >= 24):
  dayOffset = 1
  hourOffset = now.hour+hourDelay+secondRunOffset - 24
else:
  dayOffset = 0
  hourOffset = secondRunOffset

#Safety check, prevent overflow in scheduler
overflowDelay(now, secondDelay, minuteDelay, hourDelay)

#Print schedule and run
next_date = now.replace(day=now.day+dayDelay, hour=hourOffset, minute=now.minute+minuteDelay, second=now.second+secondDelay, microsecond=now.microsecond)
print("The time is " + str(now) + " which is run #1")
print("Next run at " + str(next_date))
mainPurpose(nextRun = next_date)

# --- End --- 
#Run ends when loop count is exceeded

