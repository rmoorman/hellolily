(function($, window, document, undefined){
    window.HLSelect2 = {
        config: {
            tagInputs: 'input.tags',
            ajaxInputs: 'input.select2ajax',
            tagsAjaxClass: 'tags-ajax',
            ajaxPageLimit: 30,
            clearText: '-- Clear --'
        },

        init: function( config ) {
            var self = this;
            // Setup configuration
            if ($.isPlainObject(config)) {
                $.extend(self.config, config);
            }
            // On initialize, setup select2
            self.setupSelect2();
            self.initListeners();
        },

        initListeners: function() {
            var self = this;
            // When modal is shown, lets instantiate the select2 in the modals
            $(document).on('shown.bs.modal', '.modal', function() {
                self.setupSelect2();
            });
        },

        setupSelect2: function() {
            // Setup select2 for non-ajaxified selects, ajaxified selects
            // are using hidden inputs.
            $('select').select2({
                // at least this many results are needed to enable the search field
                // (9 is the amount at which the user must scroll to see all items)
                minimumResultsForSearch: 9
            });
            this.createTagInputs();
            this.createAjaxInputs();
        },

        createTagInputs: function() {
            // Setup tag inputs
            $(this.config.tagInputs).each(function() {
                if (!$(this).data().hasOwnProperty('select2')) {
                    var tags = [];
                    var $this = $(this);
                    if ($this.data('choices')) {
                        tags = $this.data('choices').split(',');
                    }
                    $this.select2({
                        tags: tags,
                        tokenSeparators: [','],
                        width: '100%'
                    });
                }
            });
        },

        createAjaxInputs: function() {
            // Setup inputs that needs remote link
            var self = this;
            var cf = self.config;

            $(cf.ajaxInputs).each(function() {
                var $this = $(this);
                var _data = $this.data();
                // _data.tags is a marker for AjaxSelect2Widget which indicates
                // that it expects multiple values as input.

                // Prevent Select2 from being initialized on elements that already have Select2
                if (!_data.hasOwnProperty('select2')) {
                    var options = {
                        ajax: {
                            cache: true,
                            data: function (term, page) {
                                // page is the one-based page number tracked by Select2
                                var data = null;

                                if ($this.hasClass(cf.tagsAjaxClass) && !_data.tags) {
                                    if (term === '') {
                                        // elasticsearch breaks when the term is empty, so just look for non-empty results
                                        term = '*';
                                    }
                                    // search for contacts and accounts containing the search term, but only those with an email address
                                    var filterQuery = '((_type:contacts_contact AND (name:' + term + ' OR email_addresses.email_address:' + term + ')) ' +
                                        'OR (_type:accounts_account AND (name:' + term + ' OR email_addresses.email_address:' + term + '))) ' +
                                        'AND email_addresses.email_address:*';

                                    data = {
                                        filterquery: filterQuery,
                                        size: cf.ajaxPageLimit, // page size
                                        page: (page - 1), // page number, zero-based
                                        sort: '-modified' //sort modified descending
                                    };
                                }
                                else {
                                    var term_stripped = term.trim();
                                    data = {
                                        filterquery: term_stripped ? 'name:('+term_stripped+')' : '', //search term
                                        size: cf.ajaxPageLimit, // page size
                                        page: (page - 1), // page number, zero-based
                                        sort: '-modified' //sort modified descending
                                    };
                                }

                                var filters = $this.data('filter-on');
                                if (typeof filters !== 'undefined' && filters !== '') {
                                    filters.split(',').forEach(function (filter) {
                                        if (filter.indexOf('id_') === 0) {
                                            var filter_val = $('#' + filter).val();
                                            var filter_name = filter.substring(3);
                                            if (filter_name.indexOf('case_quickbutton_') === 0) {
                                                filter_name = filter.substring(20);
                                            } else if (filter_name == 'account') {
                                                // This is a special case at the moment, in the future we might have
                                                // more cases like this.
                                                // But for now, just do this check
                                                filter_name = 'accounts.id';
                                            }
                                            if (filter_val && filter_val > 0) {
                                                data.filterquery += ' ' + filter_name + ':' + filter_val;
                                            }
                                        } else {
                                            data.type = filter;
                                        }
                                    });
                                }

                                return data;
                            },

                            results: function (data, page) {
                                var more = (page * cf.ajaxPageLimit) < data.total; // whether or not there are more results available

                                if ($this.hasClass(cf.tagsAjaxClass) && !_data.tags) {
                                    var parsed_data = [];

                                    data.hits.forEach(function (hit) {
                                        // Only display contacts with an e-mail address
                                        for (var i = 0; i < hit.email_addresses.length; i++) {
                                            // The text which is actually used in the application
                                            var used_text = '"' + hit.name + '" <' + hit.email_addresses[i].email_address + '>';
                                            // The displayed text
                                            var displayed_text = hit.name + ' <' + hit.email_addresses[i].email_address + '>';
                                            // Select2 sends 'id' as the value, but we want to use the email
                                            // So store the actual id (hit.id) under a different name
                                            parsed_data.push({id: used_text, text: displayed_text, object_id: hit.id});
                                        }
                                    });

                                    // Array elements with empty text can't be added to select2, so manually fill a new array
                                    data.hits = parsed_data;
                                }
                                else {
                                    data.hits.forEach(function (hit) {
                                        hit.text = hit.name;
                                    });
                                }

                                // Add clear option, but not for multiple select2.
                                if ((page == 1 && !$this.hasClass(cf.tagsAjaxClass)) && !_data.tags) {
                                    data.hits.unshift({id: -1, text:cf.clearText});
                                }
                                return {
                                    results: data.hits,
                                    more: more
                                };
                            }
                        },

                        initSelection: function (item, callback) {
                            var id = item.val();
                            var text = item.data('selected-text');
                            var data = { id: id, text: text };
                            callback(data);
                        }
                    };

                    if ($this.hasClass(cf.tagsAjaxClass)) {
                        options.tags = true;
                        options.tokenSeparators = [','];
                        // Create a new tag if there were no results
                        options.createSearchChoice = function (term, data) {
                            if ($(data).filter(function () {
                                    return this.text.localeCompare(term) === 0;
                                }).length === 0) {
                                return {
                                    id: term,
                                    text: term
                                };
                            }
                        };
                        // Prevent select2 dropdown from opening when pressing enter
                        options.openOnEnter = false;
                    }

                    // Set select2 to multiple.
                    if(_data.tags) {
                        options.tags = true;
                        options.multiple = true;
                    }


                    $this.select2(options);
                    // Set the initial form value from a JSON encoded data attribute called data-initial
                    if(_data.tags) {
                        $this.select2('data', _data.initial);
                    }
                }
            });
        }
    };

})(jQuery, window, document);
