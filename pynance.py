import requests
import json
from getpass import getpass
import time

def pprint(jdata):
	print json.dumps(jdata, indent=4, sort_keys=True)

def parse_portfolio(entry):
	""" Given a blob of JSON data (as a dict) that describes a portfolio,
		return a dictionary with the important data. """
	portfolio = {
		'title' : entry['title']['$t'],
		'updated' : entry['updated']['$t'],
		'id' : entry['id']['$t'],
		'etag' : entry['gd$etag'],
		'link' : entry['link'][1]['href'],
		'feedLink' : entry['gd$feedLink']['href'],
		'portfolioData' : {},
		'positions' : {}
	}
	# Gets extra portfolio data that are stored as specific gf$NAME entries
	pred = lambda x: x[0:3]=="gf$"
	for measurement in filter(pred, entry['gf$portfolioData']):
		#print "New Measurement: {}".format(measurement)
		list_of_values = entry['gf$portfolioData'][measurement]['gd$money']
		mod_list = []
		for value in list_of_values:
			subdict = value
			subdict['amount'] = float(subdict['amount'])
			mod_list.append(subdict)
		portfolio['portfolioData'][measurement[3:]] = mod_list
	# Build the standard portfolio data
	for key, value in entry['gf$portfolioData'].iteritems():
		if key != "currencyCode" and not pred(key):
			portfolio['portfolioData'].update({key : float(value)})
	return portfolio
def print_portfolio(portData):
	""" Given a portfolio dict, print it out nice and pretty."""
	print "{}:\n  Last Updated: {}\n  Link to feed: {}".format(portData['title'], portData['updated'], portData['link'])
	for k, v in portData['portfolioData'].iteritems():
		print "    {} = {}".format(k, v)

def parse_position(entry):
	""" Given a blob of JSON data (as a dict) that descibres a position,
		return a dictionary with the important data. """
	position = {
		'id' : entry['id']['$t'],
		'updated' : entry['updated']['$t'],
		'title' : entry['title']['$t'],
		'link' : entry['link'][0]['href'],
		'feedLink' : entry['gd$feedLink']['href'],
		'symbol' : entry['gf$symbol']['symbol'],
		'exchange': entry['gf$symbol']['exchange'],
		'fullName' : entry['gf$symbol']['fullName'],
		'positionData' : {},
		'transactions' : {}
	}
	position['positionData'].update(entry['gf$positionData'])
	for key in position['positionData']:
		position['positionData'][key] = float(position['positionData'][key])
	return position
def print_position(posData):
	""" Given a position, pretty-print it."""
	print "{}:{} - {}".format(posData['exchange'], posData['symbol'], posData['title'])
	print "  Last Updated:", posData['updated']
	print "  Link to feed:", posData['feedLink']
	print "  Link:", posData['link']
	for k, v in posData['positionData'].iteritems():
		print "    {} = {}".format(k, v)

class FinanceSession():
	def __init__(self, username, password):
		self.Auth = None
		self.service = "finance"
		self.source = "peterldowns-pynance-1.0"
		self.email = username
		self.passwd = password
		self.headers = {
			'GData-Version' : '2',
			'content-type':'application/x-www-form-urlencoded',
		}
		self.portfolios = {}
		#self.positions = {}
		#self.transactions = {}
		
		self.login() # Authenticate to begin the session

	def login(self):
		""" Begin a session and retrieve a GoogleAuth key for later use.
			A user must have this key to perform any other operation. """
		print "Authenticating ..."
		target = "https://www.google.com/accounts/ClientLogin"
		payload = {
			"Email" : self.email,
			"Passwd" : self.passwd,
			"service" : self.service,
			"source" : self.source
		}
		response = requests.post(target, data=payload, headers=self.headers)
		if response.status_code == 200:
			SID, LSID, Auth = map(lambda x:x.split('=')[1], response.content.split('\n')[0:3])
			self.Auth = Auth
			self.headers["Authorization"] = ("GoogleLogin auth="+Auth)
			print "... successful!"
			return True
		else:
			#TODO: raise exception?
			print "... failed. Please retry."
			return False
	
	def get_portfolios(self):
		""" Retrieve a list of all of a user's portfolios. """
		if not self.Auth:
			print "Not authenticated!"
			return False

		target = "https://finance.google.com/finance/feeds/default/portfolios?returns=true&alt=json"
		response = requests.get(target, headers=self.headers)
		if not response.status_code == 200:
			print "Error! Response status code = {}".format(response.status_code)
			return False
		else:
			resp_data = json.loads(response.content)
			feed = resp_data['feed']
			entries = feed['entry']
			for entry in entries:
				#print json.dumps(entry, sort_keys=True, indent=4)
				port = parse_portfolio(entry)
				self.portfolios[port['title']] = port
			return True
	
	def show_portfolios(self):
		""" Prints out a list of the user's portfolios """
		if not self.portfolios:
			self.get_portfolios()
		print "Portfolios:"
		print "-----------"
		for title, port in self.portfolios.iteritems():
			print_portfolio(port)
		print "-----------"
	
	def create_portfolio(self, title, currencyCode="USD"):
		""" Create a new portfolio with a given title and base currency. """
		if not self.Auth:
			print "Not authenticated!"
			return False

		cc = currencyCode.upper()
		if len(cc) != 3:
			print "Currency code must be 3 characters. You supplied: {}".format(currencyCode)
			print "Portfolio creation failed."
			return False
		if not title: # title=="", title=None
			print "Must supply a title."
			print "Portfolio creation failed."
			return False
		
		pf_entry = "<entry xmlns='http://www.w3.org/2005/Atom' "\
						"xmlns:gf='http://schemas.google.com/finance/2007'> "\
						"<title>{}</title> "\
						"<gf:portfolioData currencyCode='{}'/> "\
					"</entry>".format(title, cc)
		target = "https://finance.google.com/finance/feeds/default/portfolios?alt=json"
		
		_headers = self.headers
		_headers['content-type'] = 'application/atom+xml' # must change content type; posting XML

		r = requests.post(target, headers=_headers, data=pf_entry)
		if r.status_code != 201:
			print "Unable to create portfolio {} (currency: {})".format(title, cc)
			print "Server returned:", r.content
			return False
		
		resp_data = json.loads(r.content)
		new_portfolio = parse_portfolio(resp_data['entry'])
		self.portfolios[new_portfolio['title']] = new_portfolio
		print "Created new portfolio: {} (currency: {})".format(title, cc)
		return True
	
	def delete_portfolio(self, title):
		""" If a portfolio with the given title currently exists: delete it. """
		if not self.Auth:
			print "Not authenticated!"
			return False

		if title in self.portfolios:
			r = requests.delete(self.portfolios[title]['link'], headers=self.headers)
			if r.status_code == 200:
				print "Successfully deleted portfolio: '{}'".format(title)
				del self.portfolios[title]
				return True
			else:
				print "Unable to delete portfolio '{}' due to a request or server error.".format(title)
				print "Status code: {}\nServer resp: {}".format(r.status_code, r.content)
		else:
			print "Portfolio '{}' does not exist.".format(title)
			print "Deletion failed."
		return False

	def get_positions(self, pftitle):
		""" Get all of the current positions of a given portfolio. """
		if not self.Auth:
			print "Not authenticated!"
			return False
		if pftitle in self.portfolios:
			pf = self.portfolios[pftitle]
			target = "{}?alt=json".format(pf['feedLink'])
			r = requests.get(target, headers=self.headers)
			if r.status_code == 200:
				pos_resp = json.loads(r.content)
				feed = pos_resp['feed']
				if  not 'entry' in feed:
					return True
				entries = feed['entry']
				for entry in entries:
					position = parse_position(entry)
					pf['positions'][position['symbol']] = position
					self.portfolios[pftitle] = pf # unnecessary? not sure if pf is a reference or copy
				#TODO: print success?
				return True
			else:
				print "Unable to fetch positions for portfolio '{}'".format(pftitle)
				print "Status code: {}\nServer resp: {}".format(r.status_code, r.content)
		else:
			print "Portfolio '{}' does not exist.".format(pftitle)
			print "Unable to fetch positions for nonexistent portfolio"
		return False
	
	def show_positions(self, pftitle):
		""" For a given portfolio, show all of the positions held within it. """
		if not self.portfolios[pftitle]:
			print "Portfolio '{}' does not exist.".format(pftitle)
			return False
		if not self.portfolios[pftitle]['positions']:
			self.get_positions(pftitle)
		
		print "Portfolio: {}".format(pftitle)
		print "Positions:"
		print "-----------"
		for title, pos in self.portfolios[pftitle]['positions'].iteritems():
			print_position(pos)
		print "-----------"

	def get_position_data(self, pftitle, symbol, exchange=None):
		""" Gets data associated with a specific position in a given portfolio.
			You must specify a symbol: e.g., 'AAPL' or 'NASDAQ:AAPL'. If preferred,
			the exchange can be passed as its own argument: symbol='AAPL', exchange='NASDAQ'
			. Do not pass the exchange within the symbol AND as its own argument. """
		if not self.Auth:
			print "Not authenticated!"
			return False
		if not pftitle in self.portfolios:
			print "Portfolio '{}' does not exist.".format(pftitle)
			print "Unable to fetch positions for nonexistent portfolio"
			return False
		# TODO: actually fetch position data?
		symbol = symbol.upper()
		if exchange:
			exchange = exchange.upper()
			matched_pos = [(name, data) for name, data in self.portfolios[pftitle]['positions'].iteritems() if symbol == data['symbol'] and exchange == data['exchange']]
		else:
			matched_pos = [(name, data) for name, data in self.portfolios[pftitle]['positions'].iteritems() if symbol == data['symbol']]
		matched_pos = dict(matched_pos)
	
		print "{} positions found for symbol {} on {} exchange".format(len(matched_pos), symbol, exchange if exchange else "any")
		for pos in matched_pos.itervalues():
			print_position(pos)
		return True

	#def get_transactions(self, pftitle, symbol, exchange=None):
		#""" Gets a list of transactions for a specific position/symbol. """
		#symbol = symbol.upper()
		#if exchange: exchange = exchange.upper()
		#if not self.Auth:
			#print "Not authenticated!"
			#return False
		#if not pftitle in self.portfolios:
			#print "Portfolio '{}' does not exist.".format(pftitle)
			#print "Unable to fetch transaction data for nonexistent portfolio"
			#return False
		#if not exchange in self.portfolios['pftitle']:
			#print "Portfolio '{}' has no positions on {} (on {} exchange)".format(pftitle, symbol, exchange if exchange else "any")
			#print "Unable to fetch transaction data for nonexistent position"
	
	def buy(self, pftitle, symbol, shares, pps, commission=None, cc="USD", ts=None):
		""" Purchase shares of a stock and add them to a portfolio. """
		return self.mk_transaction("Buy", pftitle, symbol, shares, pps, commission, cc, ts)
	def sell(self, pftitle, symbol, shares, pps, commission=None, cc="USD", ts=None):
		""" Sell shares of a stock and remove them from a portfolio. """
		return self.mk_transaction("Sell", pftitle, symbol, shares, pps, commission, cc, ts)

	def mk_transaction(self, transaction_type, pftitle, symbol, shares, pps, commission=None, cc="USD", ts=None):
		#TODO: add error checking here

		timestamp = ts if ts else time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) # optional passed in time
		if not commission:
			commission = 0.0
		entry = "<entry xmlns='http://www.w3.org/2005/Atom' "\
		    	       "xmlns:gf='http://schemas.google.com/finance/2007' "\
					   "xmlns:gd='http://schemas.google.com/g/2005'>"\
		  			"<gf:transactionData date='{timestamp}' "\
							"shares='{shares}' type='{tt}'>"\
		      			"<gf:commission>"\
			        		"<gd:money amount='{commission}' currencyCode='{cur_code}'/>"\
					    "</gf:commission>"\
						"<gf:price>"\
							"<gd:money amount='{price}' currencyCode='{cur_code}'/>"\
						"</gf:price>"\
					"</gf:transactionData>"\
					"</entry>"
		#entry = "<?xml version='1.0' encoding='UTF-8'?>" + entry
		entry = entry.format(timestamp=timestamp, shares=float(shares),
					cur_code=cc.upper(), commission=float(commission),
					price=float(pps), tt=transaction_type)

		_headers = self.headers
		_headers['content-type'] = 'application/atom+xml' # must change content type; posting XML

		target = "{}?alt=json"
		if symbol in self.portfolios[pftitle]:
			target = target.format(self.portfolios[pftitle][symbol]['feedLink'])
		else:
			target = self.portfolios[pftitle]['id']+"/positions/"+symbol+"/transactions?alt=json"
		response = requests.post(target, headers=_headers, data=entry)
		if not response.status_code == 201:
			print "Error! Response status code = {}".format(response.status_code)
			return False
		else:
			print response.content
			resp_data = json.loads(response.content)
			#pprint(resp_data)
			#feed = resp_data['feed']
			#entries = feed['entry']
			#for entry in entries:
				#print json.dumps(entry, sort_keys=True, indent=4)
				#port = parse_portfolio(entry)
				#self.portfolios[port['title']] = port
			#return True


def test_session():
	fs = FinanceSession(raw_input("Email: "), getpass("Password: "))
	fs.get_portfolios()
	#fs.show_portfolios()
	
	#p_name = "Testing (FS) "+str(time.time())
	#fs.create_portfolio(p_name, "USD")
	
	#fs.show_portfolios()
	#for pf in fs.portfolios:
		#fs.show_positions(pf)
	#fs.get_position_data('My Portfolio', 'AAPL')
	#fs.get_position_data('My Portfolio', 'AAPL', exchange='NASDAQ')
	
	fs.show_positions('My Portfolio')
	
	fs.buy('My Portfolio', 'NASDAQ:GOOG', 500, 450.54)
	fs.show_positions('My Portfolio')
	
	fs.sell('My Portfolio', 'NASDAQ:GOOG', 500, 450.54)
	fs.show_positions('My Portfolio')
	
	# cleanup
	for pf in fs.portfolios.keys():
		if pf != 'My Portfolio':
			fs.delete_portfolio(pf)

	#print json.dumps(fs.portfolios, indent=4, sort_keys=True)
	print "................"
	print "Done."

if __name__=="__main__":
	test_session()
