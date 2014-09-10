// Handle the status selection.
$(document).ready(function() {
    // inner function to protect the scope for currentStatus
    (function($) {
        var currentStatus = $('input[name=radio]:checked', '#case-status').closest('label').attr('for');
        $('#case-status').click(function(event) {
            var radio_element = $('#' + $(event.target).closest('label').attr('for'));
            if( radio_element.attr('id') != currentStatus ) {
                // try this
                var jqXHR = $.ajax({
                    url: '/cases/update/status/' + $(radio_element).closest('#case-status').data('object-id') + '/',
                    type: 'POST',
                    data: {
                        'status': $(radio_element).val()
                    },
                    beforeSend: addCSRFHeader,
                    dataType: 'json'
                });
                // on success
                jqXHR.done(function(data, status, xhr) {
                    currentStatus = radio_element.attr('id');
                    $('#status').text(data.status);
                    // loads notifications if any
                    load_notifications();
                });
                // on error
                jqXHR.fail(function() {
                    // reset selected status
                    $(radio_element).attr('checked', false);
                    $(radio_element).closest('label').removeClass('active');
                    $('#' + currentStatus).attr('checked', true);
                    $('#' + currentStatus).closest('label').addClass('active');
                    // loads notifications if any
                    load_notifications();
                });
                // finally do this
                jqXHR.always(function() {
                    // remove request object
                    jqXHR = null;
                });
            }
        });
    })($);
});
