// Handle the stage selection.
$(document).ready(function() {
    // inner function to protect the scope for currentStage
    (function($) {
        var currentStage = $('input[name=radio]:checked', '#deal-stage').closest('label').attr('for');
        $('#deal-stage').click(function(event) {
            var radio_element = $('#' + $(event.target).closest('label').attr('for'));
            if( radio_element.attr('id') != currentStage ) {
                // try this
                var jqXHR = $.ajax({
                    url: '/deals/update/stage/' + $(radio_element).closest('#deal-stage').data('object-id') + '/',
                    type: 'POST',
                    data: {
                        'stage': $(radio_element).val()
                    },
                    beforeSend: addCSRFHeader,
                    dataType: 'json',
                });
                // on success
                jqXHR.done(function(data, status, xhr) {
                    currentStage = radio_element.attr('id');
                    $('#status').text(data.stage);
                    // check for won/lost and closing date
                    if( data.closed_date ) {
                        $('#closed-date').text(data.closed_date);
                        $('#closed-date').removeClass('hide');
                        $('#expected-closing-date:visible').addClass('hide');
                    } else {
                        $('#closed-date').text('');
                        $('#closed-date:visible').addClass('hide');
                        $('#expected-closing-date').removeClass('hide');
                    }
                    // loads notifications if any
                    load_notifications();                    
                });
                // on error
                jqXHR.fail(function() {
                    // reset selected stage
                    $(radio_element).attr('checked', false);
                    $(radio_element).closest('label').removeClass('active');
                    $('#' + currentStage).attr('checked', true);
                    $('#' + currentStage).closest('label').addClass('active');
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
