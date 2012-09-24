#!/usr/bin/python

import locale, os, sys
import ConfigParser
import tweepy

CONFIG_FILE='tweetcloner.cfg'

class TweetCloner:
	TWEETCLONER_CONSUMER_KEY='SscEYZXGFrof1Hzt8j9EOQ'
	TWEETCLONER_CONSUMER_SECRET='8dbW5YzqVEyaXlctGKNEMmNb4sB5DP0UKXzE3qVZDY'

	def __init__(self, configfile):
		self.src_account = ""
		self.dst_accounts = []
		self.initial_tweetcount = 1
		self.dryrun = False
		self.configfile = configfile
		self.read_config(configfile)

	def set_src(self, src):
		self.src_account = src

	def add_dst(self, dst):
		self.dst_accounts.append(dst)

	def set_dryrun(self, dryrun):
		self.dryrun = dryrun

	def get_dryrun(self):
		return self.dryrun

	def get_initial_tweetcount(self):
		return self.initial_tweetcount

	def set_initial_tweetcount(self, count):
		self.initial_tweetcount = count

	def read_config(self, configfile):
		if not os.access(CONFIG_FILE, os.R_OK | os.W_OK):
			sys.stderr.write('ERROR: Cannot read or write configfile "{0}".\n'.format(self.configfile))
			sys.exit(1)

		self.config = ConfigParser.ConfigParser()
		self.config.read(configfile)

	def save_config(self):
	  	with open(self.configfile, 'wb') as cfg:
			self.config.write(cfg)

	def check_config(self):	
		self.check_cfg_section(self.src_account)
		for dst_account in self.dst_accounts:
			self.check_cfg_section(dst_account)

	def check_cfg_section(self, section):
		if not self.config.has_section(section):
			sys.stderr.write('Cannot find section for account "{0}" in configfile "{1}".\n'.format(section, self.configfile))
			answer = raw_input('Do you want to add a new section for "{0}" as a new twitter account? (y/N): '.format(section)).strip()
			if answer == 'y':
				self.config.add_section(section)
				self.config.set(section, "consumer_key", self.TWEETCLONER_CONSUMER_KEY)
				self.config.set(section, "consumer_secret", self.TWEETCLONER_CONSUMER_SECRET)
				self.save_config()
			else:
				sys.stderr.write('ERROR: Account not found. Exit.\n')
				sys.exit(1)

		if not self.config.has_option(section, 'access_key') or not self.config.has_option(section, 'access_secret'):
			print 'Missing access_key and/or access_secret for {0}, requesting new token...'.format(section)
			self.oauth_app(section)
	
	def get_api(self, service):
		if not self.config.has_option(service, 'consumer_key') or not self.config.has_option(service, 'consumer_secret'):
			sys.stderr.write('ERROR: Missing consumer_key and/or consumer_secret for {0} in configfile "{1}".\n'.format(service, self.configfile))
			sys.exit(1)
	
		auth = tweepy.OAuthHandler(self.config.get(service, 'consumer_key'), 
			self.config.get(service, 'consumer_secret'), 'oob')
		
		s_host = auth.OAUTH_HOST
		s_oroot = auth.OAUTH_ROOT
		s_aroot = '/1'
	
		if self.config.has_option(service, 'host'):
			s_host = self.config.get(service, 'host') 
		if self.config.has_option(service, 'oauth_root'):
			s_oroot = self.config.get(service, 'oauth_root')
		if self.config.has_option(service, 'api_root'):
			s_aroot = self.config.get(service, 'api_root')
	
		auth.OAUTH_HOST = s_host
		auth.OAUTH_ROOT = s_oroot
		auth.secure = True 
	
		auth.set_access_token(self.config.get(service, 'access_key'), 	
			self.config.get(service, 'access_secret'))
	
		return tweepy.API(auth, host = s_host, api_root = s_aroot, secure = True)
	
	def save_access_token(self, auth, service):
		auth_url = auth.get_authorization_url()
	
		print 'Please authorize TweetCloner app at: \n ' + auth_url
		pin = raw_input('Please enter PIN: ').strip()
	
		auth.get_access_token(pin)
		print '* Saving access_key and acess_secret for account "{0}" in configfile.'.format(service)
		self.config.set(service, 'access_key', auth.access_token.key)
		self.config.set(service, 'access_secret', auth.access_token.secret)
		self.save_config()
	
	def oauth_app(self, service):
		auth = tweepy.OAuthHandler(self.config.get(service, 'consumer_key'), 
			self.config.get(service, 'consumer_secret'), 'oob')
	
		if self.config.has_option(service, 'host'):
			auth.OAUTH_HOST = self.config.get(service, 'host')
		if self.config.has_option(service, 'oauth_root'):
			auth.OAUTH_ROOT = self.config.get(service, 'oauth_root')
		auth.secure = True 
	
		self.save_access_token(auth, service)
	
	def clone(self):	
		self.check_config()

		s_api = self.get_api(self.src_account)
	
		if self.config.has_option(self.src_account, 'last_id'):
			last_id = self.config.getint(self.src_account, 'last_id')
			t_timeline = s_api.user_timeline(since_id = last_id)
		else:
			last_id = 0
			t_timeline = s_api.user_timeline(count = self.initial_tweetcount)
		
		if len(t_timeline) > 0:
			for dst_account in self.dst_accounts: 
				d_api = self.get_api(dst_account)
		
				t_timeline.reverse()
				for status in t_timeline:
					try:
						if any((True for x in self.config.get(self.src_account, 'filter').split(',') if x in status.text)):
							
							newstatus = status.text	
							for replaces in self.config.get(dst_account, 'replace').split(','):
								replace = replaces.split('=')
								newstatus = newstatus.replace(replace[0], replace[1])
							
							print '* Posting to account "{0}": "{1}"'.format(dst_account, newstatus)
							if not self.dryrun:
								d_api.update_status(newstatus)
						else:
							print '* Skipping post (filter not matched): "{0}"'.format(status.text)
					except ValueError:
						pass	
					if last_id < status.id:
						last_id = status.id
	
			if last_id > 0:
				print '* Savlng last_id of account "{0}": {1}'.format(self.src_account, last_id)
				if not self.dryrun:
					self.config.set(self.src_account, 'last_id', last_id)
					self.save_config()

def check_args():
	if len(sys.argv) < 3:
		print 'usage: {0} src_account1 dst_account1 [dst_account2 ..]'.format(sys.argv[0])
		sys.exit(1)
	
def main():
	check_args()

	tc = TweetCloner(CONFIG_FILE)
	tc.set_initial_tweetcount(1)
	tc.set_dryrun(False)
	tc.set_src(sys.argv[1])
	for i in range(2, len(sys.argv)):
		tc.add_dst(sys.argv[i])
	tc.clone()

if __name__ == '__main__':
	main()

