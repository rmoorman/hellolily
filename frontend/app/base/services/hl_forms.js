angular.module('app.services').service('HLForms', HLForms);

function HLForms () {
    /**
     * setErrors() sets the errors of the forms, making use of Angular's error handling.
     *
     * @param form (object): the form on which the errors are set
     * @param data (object): object containing all the errors
     *
     */
    this.setErrors = function (form, data) {
        for (var field in data) {
            // Errors are always in the <field>: Array format, so iterate over the array
            for (var i = 0; i < data[field].length; i++) {
                // Related fields are always an object, so check for that
                if (typeof data[field][i] === 'object') {
                    for (var key in data[field][i]) {
                        var form_field = [field, key, i].join('-');

                        // The error is always the first element, so get it and set as the error message
                        form[form_field].$error = {message: data[field][i][key][0]};
                        form[form_field].$setValidity(form_field, false);
                    }
                }
                else {
                    // Not a related field, so get the error and set validity to false
                    form[field].$error = {message: data[field][0]};
                    form[field].$setValidity(field, false);
                }
            }
        }
    };
}
