from datetime import datetime

from flask import Flask, render_template, request, redirect, flash, session, url_for
from jinja2 import evalcontextfilter, Markup
from eveapi import EVEAPIConnection, Error
from cache import DbCacheHandler
from utils import mask_check

eveapi = EVEAPIConnection(cacheHandler=DbCacheHandler())
app = Flask('apishiv')

API_ACCESS_TYPE = {
    0: 'Account Balance',
    1: 'Asset List',
    2: 'Calendar Event Attendees',
    3: 'Character Sheet',
    4: 'Standings/Contacts (PCs/Corps/Alliances)',
    5: 'Contact Notifications',
    6: 'Faction Warfare Stats',
    7: 'Industry Jobs',
    8: 'Kill Log',
    9: 'Mail Bodies',
    10: 'Mailing Lists',
    11: 'Mail Messages',
    12: 'Market Orders',
    13: 'Medals',
    14: 'Notifications',
    15: 'Notification Texts',
    16: 'Research Jobs',
    17: 'Skill In Training',
    18: 'Skill Queue',
    19: 'Standings (NPC)',
    20: 'Calendar Events',
    21: 'Wallet Journal',
    22: 'Wallet Transactions',
    23: 'Character Information',
    24: 'Private Character Information',
    25: 'Account Status',
    26: 'Contracts',
}

def auth_from_session(session):
    return eveapi.auth(keyID=session['keyid'], vCode=session['vcode'])

@app.template_filter()
@evalcontextfilter
def humanize(eval_ctx, n):
	if type(n) in [int, long, float]:
		s, ns = str(n).split('.')[0][::-1], ''
		for x in xrange(1,len(s)+1):
			ns = s[x-1]+ns
			if not x % 3 and len(s) > x: ns = ","+ns
	if eval_ctx.autoescape: ns = Markup(ns)
	return ns

@app.template_filter()
@evalcontextfilter
def unixdate(eval_ctx, n):
  ns = str(datetime.fromtimestamp(int(n)).strftime('%Y-%m-%d %H:%M:%S'))
  if eval_ctx.autoescape: ns = Markup(ns)
  return ns

@app.route('/', methods=['GET', 'POST'])
def index():
    if session.get('characters', None):
        return redirect(url_for('character_list'))
    if request.method == 'POST':
        if not request.form['keyid'] or not request.form['vcode']:
            flash('Please provide a Key and verification code')
        else:
            auth = eveapi.auth(keyID=request.form['keyid'], vCode=request.form['vcode'])
            try:
                res = auth.account.ApiKeyInfo()
            except Error as e:
                flash('Invalid KeyID/vCode, please try another')
            else:
                if res:
                    session['keyid'] = request.form['keyid']
                    session['vcode'] = request.form['vcode']
                    session['accessmask'] = res.key.accessMask
                    session['characters'] = {}

                    for c in res.key.characters:
                        session['characters'][c.characterID] = c.characterName

                    return redirect(url_for('character_list'))

    return render_template('index.html')      

@app.route('/characters')
def character_list():
    if not session.get('characters', None):
        return redirect(url_for('index'))

    auth = auth_from_session(session)
    access = []
    for id, name in API_ACCESS_TYPE.items():
        access.append((name, mask_check(session['accessmask'], id)))

    charinfo = {}
    if mask_check(session['accessmask'], 3):
        for id, name in session['characters'].items():
            res = auth.char.CharacterSheet(characterID=id)
            charinfo[id] = {'corporation': res.corporationName, 'balance': res.balance, 'sp_total': 0}
            if hasattr(res, 'allianceName') and type(res.allianceName) == unicode:
                charinfo[id]['alliance'] = res.allianceName
            for skill in res.skills:
                charinfo[id]['sp_total'] += skill.skillpoints

    if mask_check(session['accessmask'], 23):
        status = auth.account.AccountStatus()
    else:
        status = None

    return render_template('characters.html', characters=session['characters'], access=access, charinfo=charinfo, status=status)   

@app.route('/characters/<character_id>')
def character(character_id):
    if mask_check(session['accessmask'], 3):
        auth = auth_from_session(session)
        charinfo = auth.eve.CharacterInfo(characterID=character_id)
        charsheet = auth.char.CharacterSheet(characterID=character_id)
        corp = eveapi.corp.CorporationSheet(corporationID=charsheet.corporationID)
        skilltree = eveapi.eve.SkillTree()
        skilllist = {}
        for skillgroup in skilltree.skillGroups:
            for skill in skillgroup.skills:
                skilllist[skill['typeID']] = skill['typeName']
        return render_template('character.html', character=charsheet, corp=corp, skilllist=skilllist, charinfo=charinfo)
    return redirect(url_for('characters'))

@app.route('/clear')
def clear():
    session.clear()
    return redirect(url_for('index'))
