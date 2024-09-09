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

    def party(self, irc, msg, args):
        """takes no arguments

        Fetches and displays the current party odds for the presidency from electionbettingodds.com
        """
        try:
            url = "https://electionbettingodds.com/PresidentialParty2024.html"
            response = requests.get(url)
            html_content = response.text
            
            log.debug("HTML content fetched successfully.")
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            def extract_odds():
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

            republican_odds, democrat_odds, republican_change, democrat_change, rep_direction, dem_direction = extract_odds()

            if republican_odds is not None and democrat_odds is not None:
                rep_arrow = '↑' if rep_direction == 'up' else '↓'
                dem_arrow = '↑' if dem_direction == 'up' else '↓'
                rep_change_str = f" ({rep_arrow}{abs(republican_change):.1f}%)" if republican_change is not None else ""
                dem_change_str = f" ({dem_arrow}{abs(democrat_change):.1f}%)" if democrat_change is not None else ""
                response = f"Current election odds: Republican {republican_odds:.1f}%{rep_change_str}, Democrat {democrat_odds:.1f}%{dem_change_str}"
            else:
                response = "Failed to extract election odds. Check the bot's debug log for more information."

            irc.reply(response)
        except Exception as e:
            irc.reply(f"An error occurred: {str(e)}")
            log.exception("Exception in party command:")

Class = EBOdds

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79: