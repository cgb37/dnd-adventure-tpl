document.addEventListener('DOMContentLoaded', function () {
    var params = new URLSearchParams(window.location.search);
    var query = params.get('q');

    if (query) {
        fetch('/search.json')
            .then(response => response.json())
            .then(pages => {
                var results = pages.filter(page => {
                    return page.title.toLowerCase().includes(query.toLowerCase()) ||
                        page.content.toLowerCase().includes(query.toLowerCase());
                });

                displayResults(results);
            })
            .catch(error => console.error('Error fetching search data:', error));
    }

    function displayResults(results) {
        var searchResults = document.getElementById('search-results');
        searchResults.innerHTML = '';
        if (results.length > 0) {
            var ul = document.createElement('ul');
            results.forEach(result => {
                var li = document.createElement('li');
                var a = document.createElement('a');
                a.href = result.url;
                a.textContent = result.title;
                li.appendChild(a);
                ul.appendChild(li);
            });
            searchResults.appendChild(ul);
        } else {
            searchResults.innerHTML = '<p>No results found</p>';
        }
    }
});
