from bs4 import BeautifulSoup
import requests
import pandas as pd
import os.path
import sys
import math
import scores

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# The ID and range of a sample spreadsheet.
SAMPLE_SPREADSHEET_ID = "1mFoRynABSL416epHZq7LQ12L6CHh6VixLPOQJrTW81M"


def download_tournament_data(url, csv_file):
  r = requests.get(url)
  content = r.text

  print("Downloading", url, "to", csv_file)

  soup = BeautifulSoup(content, 'html.parser')
  table = soup.find(id="tournament-stats-0")

  result = []
  for row in table.tbody.contents:
      if (row.name != "tr"):
          continue

      result_row = []
      for col in row.contents:
          if (col.name != "td" or \
                'round-rating' in col['class'] or \
                'points' in col['class'] or \
                len(col.contents) == 0):
              continue

          data = col.contents[0]
          if (data.name is None):
              result_row.append(str(data))
          elif (data.name == 'a'):
              result_row.append(str(data.contents[0]))

      result.append(result_row)

  df = pd.DataFrame(result)
  df.to_csv(csv_file, header=False, index=False)

def make_opponents(schedule, coaches):
  opponents = []

  for s in schedule:
    opps = {}
    for c in coaches:
      for matchup in s:
          if c in matchup:
            opps[c] = list(filter(lambda n: n != c, matchup))[0]
    opponents.append(opps)

  return opponents

def get_schedule(coaches):
  """Shows basic usage of the Sheets API.
  Prints values from a sample spreadsheet.
  """
  creds = None
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
          "credentials.json", SCOPES
      )
      creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("token.json", "w") as token:
      token.write(creds.to_json())

  try:
    service = build("sheets", "v4", credentials=creds)

    data_range = "Schedule!A1:F21"
    # Call the Sheets API
    sheet = service.spreadsheets()
    result = (
        sheet.values()
        .get(spreadsheetId=SAMPLE_SPREADSHEET_ID, range=data_range)
        .execute()
    )
    values = result.get("values", [])
    if not values:
       print("No data found.")
       return

    schedule = []
    for i in range(1, 19):
      r = values[i]
      schedule.append([
         (r[2], r[3]),
         (r[4], r[5])
      ])
    opponents = make_opponents(schedule, coaches)
  except HttpError as err:
    print(err)

  return schedule, opponents

def get_lineup_data(coaches, weeks):
  """Shows basic usage of the Sheets API.
  Prints values from a sample spreadsheet.
  """
  creds = None
  data_frames = {}
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
          "credentials.json", SCOPES
      )
      creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("token.json", "w") as token:
      token.write(creds.to_json())

  try:
    _, opponents = get_schedule(coaches)
    service = build("sheets", "v4", credentials=creds)
    sheet = service.spreadsheets()

    for coach in coaches:
      data_range = coach + "!A1:J" + str(weeks+1)
      # Call the Sheets API
      result = (
          sheet.values()
          .get(spreadsheetId=SAMPLE_SPREADSHEET_ID, range=data_range)
          .execute()
      )
      values = result.get("values", [])

      if not values:
        print("No data found.")
        return

      rows = []
      for i in range(1, weeks+1):
        rows.append(values[i] + ([] if len(values[i]) == len(values[0]) else [None]))

      df = pd.DataFrame(rows, columns=values[0])

      # Clean data
      df['Week'] = df['Week'].astype(int)
      for row in values[0][2:]:
        df[row] = df[row].str.lower()
        df[row] = df[row].str.strip()

      data_frames[coach] = df
  except HttpError as err:
    print(err)

  return data_frames, opponents

def get_pdga_num_map():
    pdgaDb = pd.read_csv('data/pdga_db.csv')
    return {row['name']: row['pdga#'] for _, row in pdgaDb.iterrows()}

def get_tournaments(year=2024):
    return pd.read_csv('data/' + str(year) + '/tournaments.csv')

def get_tournament_data(year=2024):
    folder = 'data/' + str(year) + '/'
    tournaments = get_tournaments(year=year)

    data = []
    for _, t in tournaments.iterrows():
        if not isinstance(t.url, str):
          continue
        d = pd.read_csv(folder + t.file, header=None)
        d = pd.concat([d.iloc[:,0:5], d.iloc[:,-2:]], axis=1)
        d.columns=['place', 'name', 'pdga#', 'rating', 'par', 'total', 'prize']
        d['type'] = t.type
        d['week'] = t.week
        d['tournament'] = t.tournament_name
        data.append(d)

    data = pd.concat(data)

    data['points'] = data['place'].apply(scores.get_points)
    data['cash'] = data['prize'].str[1:].str.replace(',', '').astype(float).fillna(0)
    return data

def get_team_data(tournamentData, numWeeks, coaches, include_nonplaying=False):
    lineups, opponents = get_lineup_data(coaches, numWeeks)
    pdgaMap = get_pdga_num_map()

    def name_to_pdga(name):
        name = name.lower()
        name = name.strip()
        if name not in pdgaMap:
            print("Error:", name, "not found in PDGA number database")
            return None
        return pdgaMap[name]

    data = []
    for coach in lineups:
        raw = lineups[coach]
        d = []

        for w in range(numWeeks):
            row = raw.iloc[w]
            for p in range(4):
                curr = row['Start ' + str(p+1)]
                if isinstance(curr, str):
                    d.append((row.Week, curr, name_to_pdga(curr), 'start', opponents[w][coach]))
                else:
                    d.append(None)

            for p in range(3):
                curr = row['Bench ' + str(p+1)]
                if isinstance(curr, str):
                    d.append((row.Week, curr, name_to_pdga(curr), 'bench', opponents[w][coach]))
                else:
                    d.append(None)

            if (not pd.isnull(row['Injury Reserve'])):
                d.append((row.Week, row['Injury Reserve'], name_to_pdga(row['Injury Reserve']), 'injury', opponents[w][coach]))

        d = pd.DataFrame(d, columns=['week', 'entered_name', 'pdga#', 'status', 'opponent'])
        d['coach'] = coach
        data.append(d)

    teamData = pd.concat(data)
    result = pd.merge(teamData, tournamentData, on=['week', 'pdga#'], how=('left' if include_nonplaying else 'inner'))
    result['cash'] = result['cash'].fillna(0)
    result['points'] = result['points'].fillna(0)
    return result

if __name__ == "__main__":
  if len(sys.argv) != 2:
     print("Include year as argument.")
     exit(-1)
  year = int(sys.argv[1])

  print("Downloading all tournament data...")
  tournaments = get_tournaments(year=year)

  for _, t in tournaments.iterrows():
    if not isinstance(t.url, str):
      continue
    download_tournament_data(t['url'], 'data/' + str(year) + '/' + t['file'])
