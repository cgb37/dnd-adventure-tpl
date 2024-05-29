document.addEventListener('DOMContentLoaded', function () {
    var navItems = document.querySelectorAll('nav ul li a');

    navItems.forEach(function (navItem) {
        navItem.addEventListener('click', function (event) {
            // Close all dropdowns if the clicked item doesn't have a submenu
            if (!navItem.nextElementSibling || !navItem.nextElementSibling.matches('ul')) {
                document.querySelectorAll('nav ul li').forEach(function (li) {
                    li.classList.remove('active');
                });
                return;
            }

            // Prevent default behavior for items with submenus
            event.preventDefault();

            // Toggle the active class on the clicked item
            var parentLi = navItem.parentElement;
            var isActive = parentLi.classList.contains('active');

            // Close all dropdowns
            document.querySelectorAll('nav ul li').forEach(function (li) {
                li.classList.remove('active');
            });

            // If the clicked item was not already active, make it active
            if (!isActive) {
                parentLi.classList.add('active');
            }
        });
    });

    // Close dropdown if clicking outside
    document.addEventListener('click', function (event) {
        var isClickInside = event.target.closest('nav');
        if (!isClickInside) {
            document.querySelectorAll('nav ul li').forEach(function (li) {
                li.classList.remove('active');
            });
        }
    });
});