require 'json'
require 'digest'

module Jekyll
  class SearchJsonGenerator < Generator
    safe true

    def generate(site)
      search_data = []

      site.collections['pages'].docs.each do |page|
        if page.data['search'] == true
          search_data << {
            title: page.data['title'],
            url: page.url,
            content: page.content.gsub(/<[^>]*>/, '').gsub("\n", ' ').strip
          }
        end
      end

      search_data_json = JSON.pretty_generate(search_data)
      search_data_hash = Digest::SHA256.hexdigest(search_data_json)

      current_hash = ''
      if File.exist?('search.json')
        current_hash = Digest::SHA256.hexdigest(File.read('search.json'))
      end

      # Only regenerate search.json if its content has changed
      if current_hash != search_data_hash
        File.open('search.json', 'w') do |file|
          file.write(search_data_json)
        end
        Jekyll.logger.info "Regenerated search.json"
      else
        Jekyll.logger.info "No changes to search.json"
      end
    end
  end
end