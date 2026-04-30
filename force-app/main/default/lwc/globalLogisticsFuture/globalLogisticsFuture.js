import { LightningElement, track } from 'lwc';

const STORAGE_KEY = 'glo_chat_open';

export default class GlobalLogisticsFuture extends LightningElement {
    @track isChatOpen = false;

    connectedCallback() {
        try {
            this.isChatOpen = sessionStorage.getItem(STORAGE_KEY) === 'true';
        } catch (e) {
            // sessionStorage unavailable (e.g. private mode restrictions)
        }
    }

    handleOpenChat() {
        this.isChatOpen = true;
        this._persist();
    }

    handleCloseChat() {
        this.isChatOpen = false;
        this._persist();
    }

    _persist() {
        try {
            sessionStorage.setItem(STORAGE_KEY, String(this.isChatOpen));
        } catch (e) {
            // ignore
        }
    }
}
