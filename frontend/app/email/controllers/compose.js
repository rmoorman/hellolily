angular.module('app.email').config(emailConfig);
emailConfig.$inject = ['$stateProvider'];
function emailConfig ($stateProvider) {
    // TODO: LILY-XXX: Clean up compose states and make email/template optional params
    $stateProvider.state('base.email.compose', {
        url: '/compose',
        views: {
            '@base.email': {
                templateUrl: '/messaging/email/compose/',
                controller: EmailComposeController,
                controllerAs: 'vm'
            }
        }
    });
    $stateProvider.state('base.email.composeEmail', {
        url: '/compose/{email}',
        views: {
            '@base.email': {
                templateUrl: '/messaging/email/compose/',
                controller: EmailComposeController,
                controllerAs: 'vm'
            }
        }
    });
    $stateProvider.state('base.email.composeEmailTemplate', {
        url: '/compose/{email}/{template}',
        views: {
            '@base.email': {
                templateUrl: '/messaging/email/compose/',
                controller: EmailComposeController,
                controllerAs: 'vm'
            }
        }
    });
    $stateProvider.state('base.email.draft', {
        url: '/draft/{id:[0-9]{1,}}',
        params: {
            messageType: 'draft'
        },
        views: {
            '@base.email': {
                templateUrl: function(elem, attr) {
                    return '/messaging/email/draft/' + elem.id + '/';
                },
                controller: EmailComposeController,
                controllerAs: 'vm'
            }
        }
    });
    $stateProvider.state('base.email.reply', {
        url: '/reply/{id:[0-9]{1,}}',
        params: {
            messageType: 'reply'
        },
        views: {
            '@base.email': {
                templateUrl: function(elem, attr) {
                    return '/messaging/email/reply/' + elem.id + '/';
                },
                controller: EmailComposeController,
                controllerAs: 'vm'
            }
        }
    });
    $stateProvider.state('base.email.replyOtherEmail', {
        url: '/reply/{id:[0-9]{1,}}/{email}',
        params: {
            messageType: 'reply'
        },
        views: {
            '@base.email': {
                templateUrl: function(elem, attr) {
                    return '/messaging/email/reply/' + elem.id + '/';
                },
                controller: EmailComposeController,
                controllerAs: 'vm'
            }
        }
    });
    $stateProvider.state('base.email.replyAll', {
        // TODO: This should probably be redone so the url is nicer.
        // Maybe we can save the action in the scope?
        url: '/replyall/{id:[0-9]{1,}}',
        params: {
            messageType: 'reply-all'
        },
        views: {
            '@base.email': {
                templateUrl: function(elem, attr) {
                    return '/messaging/email/replyall/' + elem.id + '/';
                },
                controller: EmailComposeController,
                controllerAs: 'vm'
            }
        }
    });
    $stateProvider.state('base.email.forward', {
        url: '/forward/{id:[0-9]{1,}}',
        params: {
            messageType: 'forward'
        },
        views: {
            '@base.email': {
                templateUrl: function(elem, attr) {
                    return '/messaging/email/forward/' + elem.id + '/';
                },
                controller: EmailComposeController,
                controllerAs: 'vm'
            }
        }
    });
}

angular.module('app.email').controller('EmailComposeController', EmailComposeController);

EmailComposeController.$inject = ['$scope', '$state', '$stateParams', '$templateCache', '$q', 'ContactDetail', 'EmailMessage', 'EmailTemplate', 'SelectedEmailAccount'];
function EmailComposeController ($scope, $state, $stateParams, $templateCache, $q, ContactDetail, EmailMessage, EmailTemplate, SelectedEmailAccount) {
    var vm = this;

    $scope.conf.pageTitleBig = 'Send email';
    $scope.conf.pageTitleSmall = 'sending love through the world!';

    vm.discard = discard;

    activate();

    //////////

    function activate () {
        // Remove cache so new compose will always hit the server
        $templateCache.remove('/messaging/email/compose/');

        if ($stateParams.messageType == 'reply') {
            // If it's a reply, load the email message first
            EmailMessage.get({id: $stateParams.id}).$promise.then(function (emailMessage) {
                _initEmailCompose(emailMessage);
            });
        }
        else {
            // Otherwise just initialize the email compose
            _initEmailCompose();
        }
    }

    function _initEmailCompose(emailMessage) {
        var email = $stateParams.email;

        var promises = [];

        var recipient = null;
        var contactPromise;

        if (emailMessage) {
            contactPromise = ContactDetail.query({filterquery: 'email_addresses.email_address:' + emailMessage.sender.email_address}).$promise;
            promises.push(contactPromise);
        }
        else if (email) {
            contactPromise = ContactDetail.query({filterquery: 'email_addresses.email_address:' + email}).$promise;
            promises.push(contactPromise);
        }

        var emailTemplatePromise = EmailTemplate.query().$promise;
        promises.push(emailTemplatePromise);

        // TODO: LILY-XXX: Check if this can be cleaned up
        // Once all promises are done, continue
        $q.all(promises).then(function(results) {
            var templates;
            // This part should only be executed if we've loaded a contact
            if(contactPromise) {
                var contact = results[0][0];
                templates = results[1];

                if (emailMessage && !email) {
                    email = emailMessage.sender.email_address;
                }

                if (contact) {
                    // The text which is actually used in the application/select2
                    var used_text = '"' + contact.name + '" <' + email + '>';
                    // The text shown in the recipient input
                    var displayed_text = contact.name + ' <' + email + '>';

                    recipient = {
                        id: used_text,
                        text: displayed_text,
                        object_id: contact.id
                    };
                } else {
                    recipient = {
                        id: email,
                        text: email,
                        object_id: null
                    };
                }
            } else {
                templates = results[0];
            }

            var template = $stateParams.template;
            // Determine whether the default template should be loaded or not
            var loadDefaultTemplate = template == undefined;

            // Set message type to given message type if available, otherwise set to message type 'new'
            var messageType = $stateParams.messageType ? $stateParams.messageType : 'new';

            HLInbox.init();
            HLInbox.initEmailCompose({
                templateList: templates,
                defaultEmailTemplateUrl: '/messaging/email/templates/get-default/',
                getTemplateUrl: '/messaging/email/templates/detail/',
                messageType: messageType,
                loadDefaultTemplate: loadDefaultTemplate,
                recipient: recipient,
                template: template
            });
            HLInbox.setSuccesURL($scope.previousState);
            if (SelectedEmailAccount.currentAccountId) {
                angular.element(HLInbox.config.emailAccountInput).select2('val', SelectedEmailAccount.currentAccountId);
            }
        });
    }

    function discard () {
        if ($scope.previousState) {
            window.location = $scope.previousState;
        } else {
            $state.go('base.email');
        }
    }
}
