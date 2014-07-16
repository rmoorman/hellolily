$(function() {
    /* show and hide form fields using two links with different data-action attributes */
    $('body').on('click', '.form .toggle-original-form-input', function() {
        var field = $(this).closest('.show-and-hide-input');

        /* hide clicked link */
        $(this).parent().addClass('hide');

        /* toggle form input */
        if($(this).data('action') == 'show') {
            /* show the other link */
            $(field).find('[data-action="hide"]').parent().removeClass('hide');

            /* show the form input */
            $(field).find('.original-form-widget').removeClass('hide');

            /* (re)enable fields */
            $(field).find(':input').removeAttr('disabled');

            var input = $(field).find(':input:visible:not([type="file"]):first');
            if(input) {
                /* adding to the end of the execution queue reliably sets the focus */
                /*  e.g. without, this only works once for select2 inputs */
                setTimeout(function() {
                    setCaretAtEnd(input);
                }, 0);
            }
        } else if($(this).data('action') == 'hide') {
            /* show the other link */
            $(field).find('[data-action="show"]').parent().removeClass('hide');

            /* hide the form input */
            $(field).find('.original-form-widget').addClass('hide');

            /* disabled fields will not be posted */
            $(field).find(':input').attr('disabled', 'disabled');
        }
    });
});
