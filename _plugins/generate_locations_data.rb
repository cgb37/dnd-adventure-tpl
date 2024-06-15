require 'yaml'
require 'digest'
require 'jekyll'

module Jekyll
  class GenerateLocationsData < Generator
    safe true

    def generate(site)
      locations = []
      locations_dir = File.join(site.source, '_pages', 'locations')

      Dir.foreach(locations_dir) do |file|
        next if file == '.' || file == '..'

        file_path = File.join(locations_dir, file)
        next unless File.file?(file_path)

        front_matter = read_front_matter(file_path)
        next if front_matter.empty?

        location_data = {
          'title' => front_matter['title'],
          'permalink' => front_matter['permalink'],
          'chapter' => front_matter['chapter'] || '',
          'episode' => front_matter['episode'] || '',
          'scene' => front_matter['scene'] || '',
          'category' => front_matter['category']
        }

        locations << location_data
      end

      # Generate the YAML data
      locations_data_yaml = YAML.dump(locations)
      locations_data_hash = Digest::SHA256.hexdigest(locations_data_yaml)

      # Check if the current file exists and read its hash
      current_hash = ''
      data_file_path = File.join(site.source, '_data', 'locations.yml')
      if File.exist?(data_file_path)
        current_hash = Digest::SHA256.hexdigest(File.read(data_file_path))
      end

      # Only regenerate _data/locations.yml if its content has changed
      if current_hash != locations_data_hash
        Dir.mkdir(File.dirname(data_file_path)) unless Dir.exist?(File.dirname(data_file_path))
        File.open(data_file_path, 'w') do |file|
          file.write(locations_data_yaml)
        end
        Jekyll.logger.info "Regenerated _data/locations.yml"
      else
        Jekyll.logger.info "No changes to _data/locations.yml"
      end
    end

    def read_front_matter(file_path)
      content = File.read(file_path)
      front_matter = content.match(/---\s*\n(.*?)\n---\s*\n/m)
      front_matter ? YAML.safe_load(front_matter[1]) : {}
    end
  end
end