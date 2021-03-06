/**
 * relativeDate filter is a filter that represents the date in a nice format
 *
 * relativeDate will return a relative date string given the date. If the
 * date is to far in the past, it will fallback to angulars $filter
 *
 * @param: date {date|string} : date object or date string to transform
 * @param: fallbackDateFormat string (optional): fallback $filter argument
 * @param: compareWithMidnight boolean (optional): should the date comparison be with midnight or not
 *
 * @returns: string : a relative date string
 *
 * usage:
 *
 * {{ '2014-11-19T12:44:15.795312+00:00' | relativeDate }}
 */
angular.module('app.filters').filter('relativeDate', relativeDate);

relativeDate.$inject = ['$filter'];
function relativeDate ($filter) {
    return function (date, fallbackDateFormat, compareWithMidnight) {
        // Get current date
        var now = new Date(),
            calculateDelta, day, delta, hour, minute, week, month, year;

        // If date is a string, format to date object
        if (!(date instanceof Date)) {
            date = new Date(date);
            if (compareWithMidnight) {
                // In certain cases we want to compare with midnight
                date.setHours(23);
                date.setMinutes(59);
                date.setSeconds(59);
            }
        }

        delta = null;
        minute = 60;
        hour = minute * 60;
        day = hour * 24;
        week = day * 7;
        month = day * 30;
        year = day * 365;

        // Calculate delta in seconds
        calculateDelta = function () {
            return delta = Math.round((date - now) / 1000);
        };

        calculateDelta();

        if (delta > day && delta < week) {
            date = new Date(date.getFullYear(), date.getMonth(), date.getDate());
            if (compareWithMidnight) {
                // In certain cases we want to compare with midnight
                date.setHours(23);
                date.setMinutes(59);
                date.setSeconds(59);
            }
            calculateDelta();
        }

        if (!fallbackDateFormat) {
            if (window.innerWidth < 992) {
                // Display as a short version if it's a small screen (tablet, smartphone, etc.)
                fallbackDateFormat = 'dd MMM. yyyy'; // Renders as 29 Jan. 2015
            }
            else {
                fallbackDateFormat = 'dd MMMM yyyy'; // Renders as 29 January 2015
            }
        }

        // Check delta and return result
        if (delta < 0) {
            switch (false) {
                case !(-delta > week):
                    return $filter('date')(date, fallbackDateFormat);
                case !(-delta > day * 2):
                    return '' + -(Math.ceil(delta / day)) + ' days ago';
                case !(-delta > day):
                    return 'yesterday';
                case !(-delta > hour):
                    return '' + -(Math.ceil(delta / hour)) + ' hours ago';
                case !(-delta > minute * 2):
                    return '' + -(Math.ceil(delta / minute)) + ' minutes ago';
                case !(-delta > minute):
                    return 'a minutes ago';
                case !(-delta > 30):
                    return '' + -delta + ' seconds ago';
                default:
                    return 'just now';
            }
        } else {
            switch (false) {
                case !(delta < 30):
                    return 'just now';
                case !(delta < minute):
                    return '' + delta + ' seconds';
                case !(delta < 2 * minute):
                    return 'a minute';
                case !(delta < hour):
                    return '' + (Math.floor(delta / minute)) + ' minutes';
                case Math.floor(delta / hour) !== 1:
                    return 'an hour';
                case !(delta < day):
                    return '' + (Math.floor(delta / hour)) + ' hours';
                case !(delta < day * 2):
                    return 'tomorrow';
                case !(delta < week):
                    return '' + (Math.floor(delta / day)) + ' days';
                case Math.floor(delta / week) !== 1:
                    return 'a week';
                default:
                    // Use angular $filter
                    return $filter('date')(date, fallbackDateFormat);
            }
        }
    }
}
