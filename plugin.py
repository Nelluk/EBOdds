"""
EBOdds: A Limnoria plugin for fetching current election odds from electionbettingodds.com

This plugin provides commands to fetch and display the current odds
for various election outcomes from electionbettingodds.com.

Commands:
    - party: Fetches and displays the current party odds for the presidency.
    - candidate: Fetches and displays the current candidate odds for the presidency.
    - house: Fetches and displays the current odds for House control.
    - all: Fetches and displays a summary of all the above odds.

Usage:
    !ebodds party
    !ebodds candidate
    !ebodds house
    !ebodds all

Dependencies:
    - requests
    - beautifulsoup4

Version: 1.2
Last Updated: 2024-09-09
"""

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import supybot.world as world
import supybot.log as log

import requests
from bs4 import BeautifulSoup
import re

class EBOdds(callbacks.Plugin):
    """Fetches current election odds from electionbettingodds.com"""

    def _fetch_and_parse(self, url, extract_function):
        try:
            response = requests.get(url)
            html_content = response.text
            soup = BeautifulSoup(html_content, 'html.parser')
            return extract_function(soup)
        except Exception as e:
            log.exception(f"Error fetching or parsing {url}: {str(e)}")
            return None

    def _extract_party_odds(self, soup):
        tables = soup.find_all('table')
        log.debug(f"Found {len(tables)} tables")
        
        odds = {}
        changes = {}
        change_directions = {}
        
        for table in tables:
            th = table.find('th')
            if th and 'Presidency 2024 (by party)' in th.text:
                log.debug("Found the correct table")
                for row in table.find_all('tr'):
                    party_img = row.find('img', src=lambda x: x and x.endswith(('.png')))
                    if party_img:
                        party = party_img['src'].split('.')[0].strip('/')
                        log.debug(f"Found party: {party}")
                        odds_p = row.find('p', style=lambda value: value and 'font-size: 55pt' in value)
                        if odds_p:
                            log.debug(f"Found odds paragraph for {party}: {odds_p}")
                            odds_text = odds_p.text.strip()
                            log.debug(f"Odds text for {party}: {odds_text}")
                            try:
                                odds[party] = float(odds_text.strip('%'))
                                log.debug(f"Parsed odds for {party}: {odds[party]}%")
                                
                                # Extract daily change
                                change_span = row.find('span', style=lambda value: value and 'font-size: 20pt' in value)
                                if change_span:
                                    change_text = change_span.text.strip()
                                    log.debug(f"Change text for {party}: {change_text}")
                                    change_match = re.search(r'([+-]?\d+\.?\d*)%', change_text)
                                    if change_match:
                                        change_value = float(change_match.group(1))
                                        change_img = change_span.find('img')
                                        if change_img:
                                            change_directions[party] = 'down' if 'red.png' in change_img['src'] else 'up'
                                        changes[party] = change_value
                                        log.debug(f"Parsed change for {party}: {changes[party]}% ({change_directions[party]})")
                                    else:
                                        log.debug(f"Could not parse change for {party}")
                                else:
                                    log.debug(f"Could not find change span for {party}")
                            except ValueError:
                                log.debug(f"Failed to parse odds for {party}: {odds_text}")
                        else:
                            log.debug(f"Could not find odds paragraph for {party}")
        
        log.debug(f"Final odds dictionary: {odds}")
        log.debug(f"Final changes dictionary: {changes}")
        log.debug(f"Final change directions dictionary: {change_directions}")
        return odds.get('REP'), odds.get('DEM'), changes.get('REP'), changes.get('DEM'), change_directions.get('REP'), change_directions.get('DEM')

    def _extract_candidate_odds(self, soup):
        tables = soup.find_all('table')
        log.debug(f"Found {len(tables)} tables")
        
        candidates = []
        
        for table in tables:
            th = table.find('th')
            if th and 'US Presidency 2024' in th.text:
                log.debug("Found the correct table for candidates")
                rows = table.find_all('tr')
                log.debug(f"Found {len(rows)} rows in the table")
                for row in rows:
                    img = row.find('img', src=lambda x: x and x.endswith('.png') and not x.endswith(('red.png', 'green.png')))
                    if img:
                        name = img['src'].split('/')[-1].split('.')[0]
                        log.debug(f"Found candidate: {name}")
                        odds_p = row.find('p', style=lambda x: x and 'font-size: 55pt' in x)
                        if odds_p:
                            odds_text = odds_p.text.strip()
                            log.debug(f"Found odds text for {name}: {odds_text}")
                            try:
                                odds = float(odds_text.strip('%'))
                                change_span = row.find('span', style=lambda x: x and 'font-size: 20pt' in x)
                                if change_span:
                                    change_text = change_span.text.strip()
                                    log.debug(f"Found change text for {name}: {change_text}")
                                    change_match = re.search(r'([+-]?\d+\.?\d*)%', change_text)
                                    if change_match:
                                        change_value = float(change_match.group(1))
                                        change_img = change_span.find('img')
                                        change_direction = 'down' if change_img and 'red' in change_img['src'] else 'up'
                                        candidates.append((name, odds, change_value, change_direction))
                                        log.debug(f"Parsed candidate: {name}, odds: {odds}%, change: {change_value}% ({change_direction})")
                                    else:
                                        log.debug(f"Could not parse change value for {name}")
                                else:
                                    log.debug(f"Could not find change span for {name}")
                            except ValueError:
                                log.debug(f"Failed to parse odds for candidate: {name}")
                        else:
                            log.debug(f"Could not find odds paragraph for {name}")
    
        log.debug(f"Final candidates list: {candidates}")
        return candidates

    def _extract_house_odds(self, soup):
        tables = soup.find_all('table')
        log.debug(f"Found {len(tables)} tables")
        
        house_odds = {}
        
        for table in tables:
            th = table.find('th')
            if th and 'House Control 2024' in th.text:
                log.debug("Found the correct table for House control")
                rows = table.find_all('tr')
                for row in rows:
                    img = row.find('img', src=lambda x: x and x.endswith('.png') and not x.endswith(('red.png', 'green.png')))
                    if img:
                        party = img['src'].split('/')[-1].split('.')[0]
                        log.debug(f"Found party: {party}")
                        odds_p = row.find('p', style=lambda x: x and 'font-size: 55pt' in x)
                        if odds_p:
                            odds_text = odds_p.text.strip()
                            log.debug(f"Found odds text for {party}: {odds_text}")
                            try:
                                odds = float(odds_text.strip('%'))
                                change_span = row.find('span', style=lambda x: x and 'font-size: 20pt' in x)
                                if change_span:
                                    change_text = change_span.text.strip()
                                    log.debug(f"Found change text for {party}: {change_text}")
                                    change_match = re.search(r'([+-]?\d+\.?\d*)%', change_text)
                                    if change_match:
                                        change_value = float(change_match.group(1))
                                        change_img = change_span.find('img')
                                        change_direction = 'down' if change_img and 'red' in change_img['src'] else 'up'
                                        house_odds[party] = (odds, change_value, change_direction)
                                        log.debug(f"Parsed {party}: odds: {odds}%, change: {change_value}% ({change_direction})")
                                    else:
                                        log.debug(f"Could not parse change value for {party}")
                                else:
                                    log.debug(f"Could not find change span for {party}")
                            except ValueError:
                                log.debug(f"Failed to parse odds for party: {party}")
                        else:
                            log.debug(f"Could not find odds paragraph for {party}")
        
        log.debug(f"Final house odds: {house_odds}")
        return house_odds

    def party(self, irc, msg, args):
        """takes no arguments

        Fetches and displays the current party odds for the presidency from electionbettingodds.com
        """
        url = "https://electionbettingodds.com/"
        odds = self._fetch_and_parse(url, self._extract_party_odds)
        if odds:
            republican_odds, democrat_odds, republican_change, democrat_change, rep_direction, dem_direction = odds
            rep_arrow = '↑' if rep_direction == 'up' else '↓'
            dem_arrow = '↑' if dem_direction == 'up' else '↓'
            rep_change_str = f" ({rep_arrow}{abs(republican_change):.1f}%)" if republican_change is not None else ""
            dem_change_str = f" ({dem_arrow}{abs(democrat_change):.1f}%)" if democrat_change is not None else ""
            response = f"Current election odds: Republican {republican_odds:.1f}%{rep_change_str}, Democrat {democrat_odds:.1f}%{dem_change_str}"
            irc.reply(response)
        else:
            irc.reply("Failed to extract party odds. Check the bot's debug log for more information.")

    def candidate(self, irc, msg, args):
        """takes no arguments

        Fetches and displays the current candidate odds for the presidency from electionbettingodds.com
        """
        url = "https://electionbettingodds.com/President2024.html"
        candidates = self._fetch_and_parse(url, self._extract_candidate_odds)
        if candidates:
            response = "Current candidate odds: "
            for name, odds, change, direction in candidates[:3]:  # Display top 3 candidates
                arrow = '↑' if direction == 'up' else '↓'
                response += f"{name} {odds:.1f}% ({arrow}{abs(change):.1f}%), "
            irc.reply(response.rstrip(', '))
        else:
            irc.reply("Failed to extract candidate odds. Check the bot's debug log for more information.")

    def house(self, irc, msg, args):
        """takes no arguments

        Fetches and displays the current odds for House control from electionbettingodds.com
        """
        url = "https://electionbettingodds.com/House2024.html"
        house_odds = self._fetch_and_parse(url, self._extract_house_odds)
        if house_odds:
            response = "Current House control odds: "
            for party, (odds, change, direction) in house_odds.items():
                arrow = '↑' if direction == 'up' else '↓'
                response += f"{party} {odds:.1f}% ({arrow}{abs(change):.1f}%), "
            irc.reply(response.rstrip(', '))
        else:
            irc.reply("Failed to extract House control odds. Check the bot's debug log for more information.")

    def all(self, irc, msg, args):
        """takes no arguments

        Fetches and displays a summary of current odds for party, top candidates, and House control from electionbettingodds.com
        """
        party_odds = self._fetch_and_parse("https://electionbettingodds.com/", self._extract_party_odds)
        candidate_odds = self._fetch_and_parse("https://electionbettingodds.com/President2024.html", self._extract_candidate_odds)
        house_odds = self._fetch_and_parse("https://electionbettingodds.com/House2024.html", self._extract_house_odds)

        response = "Current election odds: "

        if party_odds and all(party_odds):
            rep_odds, dem_odds, rep_change, dem_change, rep_direction, dem_direction = party_odds
            rep_arrow = '↑' if rep_direction == 'up' else '↓'
            dem_arrow = '↑' if dem_direction == 'up' else '↓'
            response += f"Republican {rep_odds:.1f}% ({rep_arrow}{abs(rep_change):.1f}%), "
            response += f"Democrat {dem_odds:.1f}% ({dem_arrow}{abs(dem_change):.1f}%) / "
        else:
            response += "Party odds unavailable / "

        if candidate_odds:
            response += " ".join([f"{name} {odds:.1f}% ({('↑' if direction == 'up' else '↓')}{abs(change):.1f}%)"
                                  for name, odds, change, direction in candidate_odds[:3]])
            response += " / "
        else:
            response += "Candidate odds unavailable / "

        if house_odds:
            response += "House control odds: "
            response += ", ".join([f"{party} {odds:.1f}% ({('↑' if direction == 'up' else '↓')}{abs(change):.1f}%)"
                                   for party, (odds, change, direction) in house_odds.items()])
        else:
            response += "House control odds unavailable"

        irc.reply(response.rstrip(' /'))

Class = EBOdds

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79: