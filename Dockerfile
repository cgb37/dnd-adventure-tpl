FROM jekyll/jekyll:4.2.2

# Install bundler
RUN gem install bundler

# Install specific versions of jekyll-sass-converter and sassc
RUN gem install 'jekyll-sass-converter:2.1.0' 'sassc:2.4.0'

# Clean Jekyll cache
RUN jekyll clean

# Set the working directory
WORKDIR /srv/jekyll

# Copy the Jekyll site files into the container
COPY . /srv/jekyll

# Debugging: List files in assets folder
RUN ls -la /srv/jekyll/assets
