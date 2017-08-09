# \/\/ --- Change Inputs --- \/\/

#File save location 
source_symbols = "/Users/SeanDuncan/Desktop/Professional/Stock Monitor Data/Lists/S&P500_7_4_17.csv"
fileLocation = "/Users/SeanDuncan/Desktop/Professional/Stock Monitor Data/Runs/"

#How many symbols should we pull
pullLimit = 500
loops = 7

#Time between runs, no negatives
dayDelay = 1
hourDelay = 0
minuteDelay = 0
secondDelay = 0
secondRunOffset = 14 #in hours

#Market Parameters
averageReturnForMarket = .09

#Addressing
sendMail = 1
From = "seanwithwings@gmail.com"
To = "jesse226@gmail.com"
CC = "svd5148@gmail.com"
Password = ""

# /\/\ --- Change Inputs --- /\/\

#import libraries
import csv
import urllib2
import pandas as pd
import time
import numpy
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

#For numeric type checks, especially in div growth function
def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

#Create the CSV
def monitor_market_file(source, pullCount, saveLocation, date):
  #Get the stock values of interest
  symbols = pd.read_csv(source)

  #Get the stock data via a URL, read as CSV
  urlBase = "http://download.finance.yahoo.com/d/quotes.csv?s="
  urlEnding = "&f=snderl1y"

  #Set Column Headers for data frame, first row of data
  headers = ["Symbol", "Name", "Div_Per_Share", "Earnings_Per_Share", "PE_Ratio", "Last_Trade_Price", "Dividend_Yield", "Risk_Free_10_Years", "Beta", "Average_Return_for_Market", "Dividend_Growth_Rate", "Earnings_Per_Share_Growth", "Required_Rate_of_Return", "Calculated_Value", "Value_Differential", "Calculated_Move", "Problem"]
  data = [headers]

  #Scrape risk free 10 year rate since every company uses it
  riskFreeRate10Years = riskFree10()

  #Grab the symbol data and append to the csv
  for i, row in symbols.iterrows():
      if i <= (pullCount - 1):

        #Construct URL
        url = urlBase + row['Symbol'] + urlEnding
        print("Company #" + str(i + 1) + " - Pulling data for symbol: " + row['Symbol'])
        #Grab the data, sleep for request limit
        print("    Requesting general stock info")
        response = urllib2.urlopen(url)
        comp_stats = list(csv.reader(response))

        #Strip the outside brackets, seek additional scraped info, calculated columns
        comp_stats[0].extend([ \
          #Market Stats 
          riskFreeRate10Years #Risk_Free_10_Years \
          ,getBeta(row['Symbol']) #Beta \
          ,averageReturnForMarket #Average_Return_for_Market \
          ])

        #Calculate Dividend growth rate and EPS growth
        comp_stats[0].extend([ \
          getDividendGrowth(row['Symbol']) #Dividend_Growth_Rate \
          ,getEPSGrowthRate(row['Symbol']) #Earnings_Per_Share_Growth \
          ])

        #Declare Vars for easier understanding
        C = float(comp_stats[0][7])
        D = float(comp_stats[0][8])
        E = float(comp_stats[0][9])
        F = float(comp_stats[0][10])
        G = float(comp_stats[0][11])
        H = (float(comp_stats[0][2]) if comp_stats[0][2] != "N/A" else 0)
        I = (float(comp_stats[0][3]) if comp_stats[0][3] != "N/A" else 0)
        J = (float(comp_stats[0][4]) if comp_stats[0][4] != "N/A" else 0)
        L = (float(comp_stats[0][5]) if comp_stats[0][5] != "N/A" else 0)

        #Intermediary calculations
        comp_stats[0].extend([ \
          (C + D * (E - C)) #Required_Rate_of_Return \
          ])

        #Declare Vars for easier understanding
        B = float(comp_stats[0][12])

        #Big calculations, make decisions
        comp_stats[0].extend([ \
           ((H / (1+B)) + \
           (H * ((1+F) ** 2) / ((1+B)**2)) + \
           (H * ((1+F) ** 3) / ((1+B)**3)) + \
           (I * ((1+G) ** 3) * J / (1+B) ** 3 )) #Calculated value \
          ])

        #Declare Vars for easier understanding
        Z = comp_stats[0][13]

        #Store final calculated value
        comp_stats[0].extend([ \
          Z - L #Value_Differential \ 
          ])

        #If value > 0 then worth buying
        if ((Z - L) > 0 ):
          comp_stats[0].extend([ \
          "Yes" #Calculated_Move 
          ])
        else:
          comp_stats[0].extend([ \
          "No" #Calculated_Move 
          ])
        
        #Problem checks 
        problems = ""
        if (comp_stats[0][2] == "N/A"):
          problems = problems + "No Div Per Share, "
        if (comp_stats[0][3] == "N/A"):
          problems = problems + "No EPS, "
        if (comp_stats[0][4] == "N/A"):
          problems = problems + "No PE, "
        if (comp_stats[0][5] == "N/A"):
          problems = problems + "No Last Trade Price, "
        if (comp_stats[0][8] == 99 or comp_stats[0][8] == 999 or comp_stats[0][8] == 9999):
          problems = problems + "No Beta, "
        if (comp_stats[0][10] == 99):
          problems = problems + "No Dividends, "
        if (comp_stats[0][11] == 99 or comp_stats[0][11] == 999):
          problems = problems + "Class Stock, "
        if (problems == ""):
          problems = problems + "None"
        else:
          problems = problems[:-2]

        #Add list of problems if any
        comp_stats[0].extend([problems])
          
        #Append each list of data to our existing file
        data.append(comp_stats[0])
        print("    Resting for API request limit")
        time.sleep(6)

  #Write the dataframe to a csv
  print(saveLocation + 'test_' + str(date) + '.csv')
  with open(saveLocation + '/test_' + str(date) + '.csv', 'w') as csvfile:
    file = csv.writer(csvfile, delimiter = ',')
    file.writerows(data)

def riskFree10():
  #Grabs html tree, seaches for identifer of earnings table, grows next year est growth
  print("Scraping risk free 10 year rate")
  page = requests.get('https://www.bloomberg.com/quote/USGG10YR:IND')
  tree = html.fromstring(page.content)
  values = tree.xpath("//div[@class='price']/text()")

  #check to make sure value exists
  return (float(values[0]) / 100)

def getBeta(ID):
  #Check for class stocks, return 99 if no 
  if (ID.find(".") > 0):
    return 99

  #Grabs html tree, seaches for identifer of earnings table, grows next year est growth
  print("    Scraping beta value")
  page = requests.get('https://www.google.com/finance?q=' + ID)
  tree = html.fromstring(page.content)
  values = tree.xpath('//td[@class="val"]/text()')

  #check to make sure value exists
  if (len(values) == 0 or values[9] == "N/A" or values[9] == "-" or values[9] == ""):
    return 999

  #Remove symbols 
  betaVal = values[9]
  betaVal = betaVal.replace("%","")
  betaVal = betaVal.replace(",","")
  if (is_number(values[9])):
    betaVal = float(betaVal)
    return(betaVal)
  else:
    return(9999)

def getEPSGrowthRate(ID):
  #Check for class stocks, return 99 if no 
  if (ID.find(".") > 0):
    return 99

  #Grabs html tree, seaches for identifer of earnings table, grows next year est growth
  print("    Scraping EPS growth")
  page = requests.get('https://finance.yahoo.com/quote/' + ID + '/analysts?p=' + ID)
  tree = html.fromstring(page.content)
  values = tree.xpath('//td[@class="Ta(end) Py(10px)"]/text()')

  #check to make sure value exists
  if (len(values) == 0 or values[12] == "N/A" ):
    return 999

  #Remove symbols and bring down to percentage
  growth = values[12]
  growth = growth.replace("%","")
  growth = growth.replace(",","")
  growth = float(growth) / 100

  #This is the next year growth rate
  return (growth)

def getDividendGrowth(ID):
  #Current date for unix second differential
  now = datetime.now()

  #End, current unix timestamp
  endCode = int(time.time())

  #Start, can only pull 6 months at a time 
  passedSeconds = date(now.year, now.month, now.day) - date(now.year - 6, now.month, now.day)
  passedSeconds = int(passedSeconds.total_seconds())
  startCode = endCode - passedSeconds
  
  #The Dividend URL page
  print("    Scraping historical dividends")
  url = "https://finance.yahoo.com/quote/" + ID + "/history?period1=" + str(startCode) + "&period2=" + str(endCode) + "&interval=1mo&filter=history&frequency=1mo"
  r = requests.get(url)

  # Turn the HTML into a Beautiful Soup object, strip out items into list with dividend identifier
  soup = BeautifulSoup(r.text, 'lxml')
  table = soup.find_all(class_='Ta(c) Py(10px)')

  #Parse out the number values
  i = 0
  dividends = []
  blankDivs = 0
  temp = -1 # negative so we don't clear the first check
  string = "Null" #similar to temp, start with non-number
  while (i < len(table)):
    #Protect from stock splits
    if ("Stock Split" not in str(table[i])):
      #Some parsing to get to the number using common tags
      #print(str(table[i]))
      string = str(table[i])
      string = string[string.index("strong data-reactid="):]
      string = string[string.index(">") + 1:]
      if (string.index("</strong>") > 1 and string.index("Dividend") > 1):
        string = float(string[:string.index("</strong>")])
        #Find growth rate quarterly, or however it is published
        if ( is_number(temp) and temp > 0 and is_number(string)):
          dividends.extend([temp / string])
      else:
        blankDivs = blankDivs + 1
    else:
      blankDivs = blankDivs + 1

    #Store the value for the next iteration, don't store a non-numeric value
    if (is_number(string)):
      temp = string
    i = i + 1

  #Average growth rate to get our estimate, if no dividens then give 99 to filter out
  if (len(dividends) != 0):
    #Annualize adjustment
    quartersPassed = passedSeconds / 60 / 60 / 24 / 91.31 #91 = days in quarter
    adjustMult = ( quartersPassed / float(len(table) - blankDivs) )
    #Subtract 1 for growth > 1, 4 since assuming quarterly divs, x multiplier to inc for missed quarters
    return ((sum(dividends) / len(dividends) - 1) * 4 * adjustMult )
  else:
    return 99 

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
  print("--- TO: " + emailTo + " | CC: " + emailCC + " | FROM: " + emailFrom )

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


