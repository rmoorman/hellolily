angular.module('app.preferences').config(preferencesConfig);

preferencesConfig.$inject = ['$stateProvider'];
function preferencesConfig($stateProvider) {
    $stateProvider.state('base.preferences.emailtemplates', {
        url: '/emailtemplates',
        views: {
            '@base.preferences': {
                templateUrl: 'preferences/controllers/emailtemplate_list.html',
                controller: PreferencesEmailTemplatesList
            }
        },
        ncyBreadcrumb: {
            label: 'Email templates'
        }
    });
}

angular.module('app.preferences').controller('PreferencesEmailTemplatesList', PreferencesEmailTemplatesList);

PreferencesEmailTemplatesList.$inject = ['$modal', '$scope', 'EmailTemplate'];
function PreferencesEmailTemplatesList ($modal, $scope, EmailTemplate) {
    //$scope.conf.pageTitleBig = 'EmailTemplate settings';
    //$scope.conf.pageTitleSmall = 'the devil is in the details';

    EmailTemplate.query({}, function(data) {
        $scope.emailTemplates = data;
    });

    $scope.makeDefault = function(emailTemplate) {
        // TODO: LILY-756: Make this controller more Angular
        var modalInstance = $modal.open({
            templateUrl: '/messaging/email/templates/set-default/' + emailTemplate.id + '/',
            controller: 'PreferencesSetTemplateDefaultModal',
            size: 'lg',
            resolve: {
                emailTemplate: function () {
                    return emailTemplate;
                }
            }
        });

        modalInstance.result.then(function () {
            $state.go($state.current, {}, {reload: false});
        }, function () {
        });
    };

    $scope.deleteEmailTemplate = function(emailtemplate) {
        if (confirm('Are you sure?')) {
            EmailTemplate.delete({
                id: emailtemplate.id
            }, function() {  // On success
                var index = $scope.emailTemplates.indexOf(emailtemplate);
                $scope.emailTemplates.splice(index, 1);
            }, function(error) {  // On error
                alert('something went wrong.')
            })
        }
    };
}
