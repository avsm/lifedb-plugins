require 'rubygems'
require 'nokogiri'
require 'mechanize'
require 'time'

$fbUrl = "http://www.facebook.com"
$agent = WWW::Mechanize.new
$agent.user_agent_alias  = "Mac FireFox"
$username = "nick@recoil.org"
$password = nil

WWW::Mechanize.html_parser = Nokogiri::HTML

def login
  puts "Logging in..."
  page = $agent.get($fbUrl)

  if(page.title == "Welcome to Facebook! | Facebook")
    loginf = page.form('menubar_login')
    loginf.email = $username
    loginf.pass = $password
    login_result_page = $agent.submit(loginf, loginf.buttons.first)

    # Return true if we've arrived at the home page
    (login_result_page.title == "Facebook | Home")
  end
end

# Returns a list of the pagination links at the footer of the FB mail page
def get_pagination_links(mail_page)
  mail_page.search('ul.pagerpro li a').collect
end

# Returns a list of message links for this page
def get_message_links(mail_page)
  puts "Getting message links..."
  mail_page.search('table#megaboxx tr').collect { |x| x.search("div.subject_wrap a").first }
end

def random_sleep
  duration = ((rand * 10) + 4).to_i
  puts "[ sleeping for #{duration}s ]"
  sleep duration
end

def parse_message_page(message_page)
  message_subject = message_page.search(".thread_header h2.subject").first.child.content

  message_page.search("div.message").each do |message|
    sender_href = message.search(".author_info .name a").first['href']

    message_date = Time.parse(message.search(".author_info .date").first.content)
    message_body = message.search(".body .text").first.content
    message_from_facebook_name = message.search(".author_info .name").first.content
    
    if sender_href =~ /id=(\d+)$/
      message_from_facebook_id = $1
    else
      message_from_facebook_id = -1
    end
    
    puts "From: #{message_from_facebook_name} (#{message_from_facebook_id})"
    puts "Subject: #{message_subject}"
    puts "Sent on: #{message_date}"
    puts 
    puts message_body
    puts
    puts "------------------------"
    puts 
  end
end

if $password.nil?
  puts "You need to edit the code and provide your password in $password, until I can get the password accessed via the keychain"
  exit
end

login_result = login()

puts "Logging in was a #{login_result}"

mail_page = $agent.get("http://www.facebook.com/inbox/")

pages_to_traverse = get_pagination_links(mail_page)

messages_to_traverse = get_message_links(mail_page)

messages_to_traverse.each do |message|
  random_sleep()
  puts "[ Parsing #{message['href']} ]"
  
  message_page = $agent.get(message['href'])
  parse_message_page(message_page)
end
 
