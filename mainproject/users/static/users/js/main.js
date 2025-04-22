// Main JavaScript file for the users app

document.addEventListener('DOMContentLoaded', function () {
    // Add any JavaScript functionality here
    console.log('Users app JavaScript loaded');

    // Example: Add fade effect to messages
    const messages = document.querySelectorAll('.messages li');
    if (messages.length > 0) {
        setTimeout(function () {
            messages.forEach(function (message) {
                message.style.transition = 'opacity 1s';
                message.style.opacity = '0';
            });
        }, 3000);
    }

    // User dropdown toggle
    const userProfile = document.querySelector('.user-profile h3');
    const userDropdown = document.querySelector('.user-dropdown');

    if (userProfile && userDropdown) {
        userProfile.addEventListener('click', function () {
            userDropdown.classList.toggle('active');
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', function (event) {
            if (!userProfile.contains(event.target) && !userDropdown.contains(event.target)) {
                userDropdown.classList.remove('active');
            }
        });
    }

    // Highlight active sidebar item
    const currentPath = window.location.pathname;
    const sidebarLinks = document.querySelectorAll('.sidebar-menu a');

    sidebarLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.parentElement.classList.add('active');
        }
    });

    // Deck creation modal functionality
    const createDeckBtn = document.getElementById('create-deck-btn');
    const createDeckModal = document.getElementById('create-deck-modal');
    const cancelCreateDeckBtn = document.getElementById('cancel-create-deck');

    if (createDeckBtn && createDeckModal) {
        createDeckBtn.addEventListener('click', function () {
            createDeckModal.style.display = 'block';
        });

        cancelCreateDeckBtn.addEventListener('click', function () {
            createDeckModal.style.display = 'none';
        });

        // Close modal when clicking outside
        window.addEventListener('click', function (event) {
            if (event.target === createDeckModal) {
                createDeckModal.style.display = 'none';
            }
        });
    }

    // Deck options menu functionality
    const optionsDots = document.querySelectorAll('.options-dots');

    optionsDots.forEach(dot => {
        dot.addEventListener('click', function (e) {
            e.stopPropagation();
            const deckId = this.getAttribute('data-deck-id');
            const optionsMenu = document.getElementById(`options-menu-${deckId}`);

            // Close all other menus first
            document.querySelectorAll('.options-menu').forEach(menu => {
                if (menu !== optionsMenu) {
                    menu.classList.remove('active');
                }
            });

            // Toggle this menu
            optionsMenu.classList.toggle('active');
        });
    });

    // Close options menu when clicking elsewhere
    document.addEventListener('click', function () {
        document.querySelectorAll('.options-menu').forEach(menu => {
            menu.classList.remove('active');
        });
    });

    // Rename deck functionality
    const renameDeckBtns = document.querySelectorAll('.rename-deck');
    const renameDeckModal = document.getElementById('rename-deck-modal');
    const cancelRenameDeckBtn = document.getElementById('cancel-rename-deck');
    const renameDeckForm = document.getElementById('rename-deck-form');

    renameDeckBtns.forEach(btn => {
        btn.addEventListener('click', function (e) {
            e.stopPropagation();
            const deckId = this.getAttribute('data-deck-id');
            renameDeckForm.action = `/users/rename-deck/${deckId}/`;
            renameDeckModal.style.display = 'block';
        });
    });

    if (cancelRenameDeckBtn) {
        cancelRenameDeckBtn.addEventListener('click', function () {
            renameDeckModal.style.display = 'none';
        });
    }

    // Delete deck functionality
    const deleteDeckBtns = document.querySelectorAll('.delete-deck');
    const deleteDeckModal = document.getElementById('delete-deck-modal');
    const cancelDeleteDeckBtn = document.getElementById('cancel-delete-deck');
    const deleteDeckForm = document.getElementById('delete-deck-form');

    deleteDeckBtns.forEach(btn => {
        btn.addEventListener('click', function (e) {
            e.stopPropagation();
            const deckId = this.getAttribute('data-deck-id');
            deleteDeckForm.action = `/users/delete-deck/${deckId}/`;
            deleteDeckModal.style.display = 'block';
        });
    });

    if (cancelDeleteDeckBtn) {
        cancelDeleteDeckBtn.addEventListener('click', function () {
            deleteDeckModal.style.display = 'none';
        });
    }

    // Close modals when clicking outside
    window.addEventListener('click', function (event) {
        if (event.target === renameDeckModal) {
            renameDeckModal.style.display = 'none';
        }
        if (event.target === deleteDeckModal) {
            deleteDeckModal.style.display = 'none';
        }
    });

    // Create card modal functionality
    const createCardBtn = document.getElementById('create-card-btn');
    const createCardModal = document.getElementById('create-card-modal');
    const cancelCreateCardBtn = document.getElementById('cancel-create-card');

    if (createCardBtn && createCardModal) {
        createCardBtn.addEventListener('click', function () {
            createCardModal.style.display = 'block';
        });

        cancelCreateCardBtn.addEventListener('click', function () {
            createCardModal.style.display = 'none';
        });

        // Close modal when clicking outside
        window.addEventListener('click', function (event) {
            if (event.target === createCardModal) {
                createCardModal.style.display = 'none';
            }
        });
    }

    // Card options menu functionality
    const cardOptionsDots = document.querySelectorAll('.card-options .options-dots');

    cardOptionsDots.forEach(dot => {
        dot.addEventListener('click', function (e) {
            e.stopPropagation();
            const cardId = this.getAttribute('data-card-id');
            const optionsMenu = document.getElementById(`card-options-menu-${cardId}`);

            // Close all other menus first
            document.querySelectorAll('.options-menu').forEach(menu => {
                if (menu !== optionsMenu) {
                    menu.classList.remove('active');
                }
            });

            // Toggle this menu
            optionsMenu.classList.toggle('active');
        });
    });

    // Edit card functionality
    const editCardBtns = document.querySelectorAll('.edit-card');
    const editCardModal = document.getElementById('edit-card-modal');
    const cancelEditCardBtn = document.getElementById('cancel-edit-card');
    const editCardForm = document.getElementById('edit-card-form');
    const editQuestionField = document.getElementById('edit_question');
    const editAnswerField = document.getElementById('edit_answer');

    editCardBtns.forEach(btn => {
        btn.addEventListener('click', function (e) {
            e.stopPropagation();
            const cardId = this.getAttribute('data-card-id');
            const question = this.getAttribute('data-question');
            const answer = this.getAttribute('data-answer');

            editCardForm.action = `/users/card/${cardId}/edit/`;
            editQuestionField.value = question;
            editAnswerField.value = answer;
            editCardModal.style.display = 'block';
        });
    });

    if (cancelEditCardBtn) {
        cancelEditCardBtn.addEventListener('click', function () {
            editCardModal.style.display = 'none';
        });
    }

    // Delete card functionality
    const deleteCardBtns = document.querySelectorAll('.delete-card');
    const deleteCardModal = document.getElementById('delete-card-modal');
    const cancelDeleteCardBtn = document.getElementById('cancel-delete-card');
    const deleteCardForm = document.getElementById('delete-card-form');

    deleteCardBtns.forEach(btn => {
        btn.addEventListener('click', function (e) {
            e.stopPropagation();
            const cardId = this.getAttribute('data-card-id');
            deleteCardForm.action = `/users/card/${cardId}/delete/`;
            deleteCardModal.style.display = 'block';
        });
    });

    if (cancelDeleteCardBtn) {
        cancelDeleteCardBtn.addEventListener('click', function () {
            deleteCardModal.style.display = 'none';
        });
    }

    // Close modals when clicking outside
    window.addEventListener('click', function (event) {
        if (event.target === editCardModal) {
            editCardModal.style.display = 'none';
        }
        if (event.target === deleteCardModal) {
            deleteCardModal.style.display = 'none';
        }
    });
}); 