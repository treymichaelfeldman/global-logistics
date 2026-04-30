import { LightningElement, track } from 'lwc';
import GLOBAL_LOGISTICS_MODERN from '@salesforce/resourceUrl/GlobalLogisticsModern';

export default class AgentforceChatWidget extends LightningElement {
    chatIcon = `${GLOBAL_LOGISTICS_MODERN}/icon-chat.svg`;
    
    @track isChatOpen = false;

    toggleChat() {
        this.isChatOpen = !this.isChatOpen;
    }
}