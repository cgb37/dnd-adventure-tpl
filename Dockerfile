FROM jekyll/jekyll:stable

# Install necessary tools
RUN apk update && apk add --no-cache build-base libffi-dev

# Install bundler
RUN gem update --system && gem install bundler

# Clean Jekyll cache
RUN jekyll clean

# Set the working directory
WORKDIR /srv/jekyll

# Copy the Jekyll site files into the container
COPY . /srv/jekyll

# Change ownership and permissions
RUN chown -R jekyll:jekyll /srv/jekyll && chmod -R 755 /srv/jekyll

# Install bundle
RUN bundle install

# Debugging: List files in assets folder and check for permissions
RUN ls -la /srv/jekyll/assets && \
    ls -la /srv/jekyll && \
    echo "Bundle Path: $(bundle show)"

# Expose port 4000
EXPOSE 4000

# Command to serve the site
CMD ["sh", "-c", "bundle install && jekyll serve --watch --livereload --incremental --force_polling --trace --verbose"]
