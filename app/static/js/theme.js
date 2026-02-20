(function() {
    'use strict';

    var STORAGE_KEY = 'theme';
    var DARK = 'dark';
    var LIGHT = 'light';
    var SYSTEM = 'system';

    function getPreference() {
        try {
            return localStorage.getItem(STORAGE_KEY) || SYSTEM;
        } catch (e) {
            return SYSTEM;
        }
    }

    function getEffectiveTheme(preference) {
        if (preference === DARK || preference === LIGHT) {
            return preference;
        }
        // System preference
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return DARK;
        }
        return LIGHT;
    }

    function applyTheme(preference) {
        var effective = getEffectiveTheme(preference);
        if (effective === DARK) {
            document.documentElement.setAttribute('data-theme', 'dark');
        } else {
            document.documentElement.removeAttribute('data-theme');
        }
    }

    function savePreference(preference) {
        try {
            localStorage.setItem(STORAGE_KEY, preference);
        } catch (e) {
            // localStorage unavailable
        }
    }

    function setTheme(preference) {
        savePreference(preference);
        applyTheme(preference);
        updateActiveButton(preference);
    }

    function updateActiveButton(preference) {
        var buttons = document.querySelectorAll('.theme-option');
        buttons.forEach(function(btn) {
            if (btn.getAttribute('data-theme-value') === preference) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
    }

    // Listen for OS theme changes (for system mode)
    if (window.matchMedia) {
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function() {
            var pref = getPreference();
            if (pref === SYSTEM) {
                applyTheme(SYSTEM);
            }
        });
    }

    // Apply on load (backup — the inline script in <head> handles FOUC prevention)
    applyTheme(getPreference());

    // Initialize settings page buttons when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        var buttons = document.querySelectorAll('.theme-option');
        if (buttons.length > 0) {
            updateActiveButton(getPreference());
            buttons.forEach(function(btn) {
                btn.addEventListener('click', function() {
                    setTheme(btn.getAttribute('data-theme-value'));
                });
            });
        }
    });

    // Expose for external use
    window.ThemeManager = {
        setTheme: setTheme,
        getPreference: getPreference,
        getEffectiveTheme: getEffectiveTheme
    };
})();
