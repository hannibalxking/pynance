import requests
import re
__OPTS = {
	#"a" : "Ask",
	"b2" : "Ask (Real-time)",
	#"b" : "Bid",
	"b3" : "Bid (Real-time)",
	#"b4" : "Book Value",
	"c1" : "Change",
	"f6" : "Float Shares",
	#"k2" : "Change Percent (Real-time)",
	#"m2" : "Day's range (Real-time)",
	#"m5" : "Change from 200-day Moving Average",
	#"m8" : "Percent Change from 50-day Moving Average",
	"n" : "Name",
	"s" : "Symbol",
	#"k1" : "Last Trade (Real-time) With Time"
	#"k3" : "Last Trade Size",
	#"a2" : "Average Daily Volume",
	#"m3" : "50-day Moving Average",
	#"m4" : "200-day Moving Average",
}
__BASE = "http://finance.yahoo.com/d/quotes.csv?s={}&f={}"


def get_stock_data(stocks, opts=None):
	if isinstance(stocks, str):
		stocks = [stocks]
	if not opts:
		opts = __OPTS.keys()
	
	reqstr = __BASE.format("+".join(stocks), "".join(opts))

	print reqstr
	r = requests.get(reqstr)
	
	if r.status_code != 200:
		raise requests.exceptions.RequestException("Response was not 200!", r)
	
	return (r.content, opts)

def clean(csv_data):
	print "RAW:"
	print csv_data
	print "_______________"
	reps = {
		r'\ +' : r' ', # collapse whitespace
		r'\r\n' : r'\n', # \n for line-endings
		#r'[\"\']' : r'', # remove all quotes
		r', ' : ',', # change ', ' to ','
	}
	for sub, rep in reps.iteritems():
		csv_data = re.sub(sub, rep, csv_data)
	
	if csv_data[-1] == '\n':
		csv_data = csv_data[:-1]
	
	return csv_data


def iterwrapper(s, delimiter=','):
	for i in s.split('\n'):
		yield i.split(delimiter)

def parse_stock_data(response):
	raw, opts = response
	raw = clean(raw)
	stock_data = {}
	
	for row in iterwrapper(raw):
		print row
		stock_dict = dict(zip(opts, row))
		print zip(opts, row)
		stock_data[stock_dict['n']] = stock_dict
	
	for stock, data in stock_data.iteritems():
		print "{}:".format(stock)
		for key, value in data.iteritems():
			print "\t{} = {}".format(__OPTS[key], value)






