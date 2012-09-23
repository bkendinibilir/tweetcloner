#!/usr/bin/python

import locale, os, sys
import ConfigParser
import tweepy

CONFIG_FILE='tweetcloner.cfg'

def save_config():
  	with open(CONFIG_FILE, 'wb') as configfile:
		config.write(configfile)

def get_twitter_api():
	tauth = tweepy.OAuthHandler(config.get('twitter', 'consumer_key'), 
		config.get('twitter', 'consumer_secret'), 'oob')

	tauth.set_access_token(config.get('twitter', 'access_key'), 
		config.get('twitter', 'access_secret'))

	return tweepy.API(tauth)

def get_api(service):
	if not config.has_option(service, 'consumer_key') or not config.has_option(service, 'consumer_secret'):
		print 'ERROR: missing consumer_key and/or consumer_secret for {0} in configfile "{1}".'.format(service, CONFIG_FILE)
		sys.exit(1)

	if not config.has_option(service, 'access_key') or not config.has_option(service, 'access_secret'):
		print 'Missing access_key and/or access_secret for {0}, requesting new token...'.format(service)
		oauth_app(service)

	auth = tweepy.OAuthHandler(config.get(service, 'consumer_key'), 
		config.get(service, 'consumer_secret'), 'oob')
	
	s_host = auth.OAUTH_HOST
	s_oroot = auth.OAUTH_ROOT
	s_aroot = '/1'

	if config.has_option(service, 'host'):
		s_host = config.get(service, 'host') 
	if config.has_option(service, 'oauth_root'):
		s_oroot = config.get(service, 'oauth_root')
	if config.has_option(service, 'api_root'):
		s_aroot = config.get(service, 'api_root')

	auth.OAUTH_HOST = s_host
	auth.OAUTH_ROOT = s_oroot
	auth.secure = True 

	auth.set_access_token(config.get(service, 'access_key'), 	
		config.get(service, 'access_secret'))

	return tweepy.API(auth, host = s_host, api_root = s_aroot, secure = True)

def save_access_token(auth, service):
	auth_url = auth.get_authorization_url()

	print 'please authorize TweetCloner App at: \n ' + auth_url
	pin = raw_input('please enter PIN: ').strip()

	auth.get_access_token(pin)
	print '* saving access_key and acess_secret for {0} in configfile'.format(service)
	config.set(service, 'access_key', auth.access_token.key)
	config.set(service, 'access_secret', auth.access_token.secret)
	save_config()

def oauth_app(service = 'twitter'):
	auth = tweepy.OAuthHandler(config.get(service, 'consumer_key'), 
		config.get(service, 'consumer_secret'), 'oob')

	if config.has_option(service, 'host'):
		auth.OAUTH_HOST = config.get(service, 'host')
	if config.has_option(service, 'oauth_root'):
		auth.OAUTH_ROOT = config.get(service, 'oauth_root')
	auth.secure = True 

	save_access_token(auth, service)

def main():
	locale.setlocale(locale.LC_ALL, 'C')

	t_api = get_api('twitter')

	if config.has_option('twitter', 'last_id'):
		last_id = config.getint('twitter', 'last_id')
		t_timeline = t_api.user_timeline(since_id = last_id)
	else:
		t_timeline = t_api.user_timeline(count = 1)
	
	if len(t_timeline) > 0:
		s_api = get_api('statusnet')

		for status in t_timeline:
			print "* posting to status.net: '{0}'".format(status.text)
			try:
				s_api.update_status(status.text)
			except ValueError:
				pass	
			last_id = status.id

		if last_id > 0:
			print "* savlng last_id: {0}".format(last_id)
			config.set('twitter', 'last_id', last_id)
			save_config()

if __name__ == '__main__':
	if os.access(CONFIG_FILE, os.R_OK | os.W_OK):
		config = ConfigParser.ConfigParser()
		config.read(CONFIG_FILE)
		main()
	else:
		print 'ERROR: cannot read or write configfile "{0}"'.format(CONFIG_FILE)
