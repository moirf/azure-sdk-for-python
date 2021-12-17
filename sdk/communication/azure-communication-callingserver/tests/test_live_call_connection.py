# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import uuid
import os
import pytest
import utils._test_constants as CONST

from azure.communication.callingserver import (
    CallingServerClient,
    PhoneNumberIdentifier,
    CallMediaType,
    CallingEventSubscriptionType,
    CommunicationUserIdentifier,
    AudioRoutingMode
    )
from azure.communication.callingserver._shared.utils import parse_connection_str
from azure.identity import DefaultAzureCredential
from _shared.testcase import (
    CommunicationTestCase,
    BodyReplacerProcessor,
    ResponseReplacerProcessor
)
from devtools_testutils import is_live
from _shared.utils import get_http_logging_policy
from utils._live_test_utils import CallingServerLiveTestUtils, RequestReplacerProcessor
from utils._test_mock_utils import FakeTokenCredential

class CallConnectionTest(CommunicationTestCase):

    def setUp(self):
        super(CallConnectionTest, self).setUp()

        if self.is_playback():
            self.from_phone_number = "+15551234567"
            self.to_phone_number = "+15551234567"
            self.recording_processors.extend([
                BodyReplacerProcessor(keys=["alternateCallerId", "targets", "source", "callbackUri", "identity", "communicationUser", "rawId", "callConnectionId", "phoneNumber", "serverCallId"])])
        else:
            self.to_phone_number = os.getenv("AZURE_PHONE_NUMBER")
            self.from_phone_number = os.getenv("ALTERNATE_CALLERID")
            self.partcipant_guid = os.getenv("PARTICIPANT_GUID")
            self.another_partcipant_guid = os.getenv("ANOTHER_PARTICIPANT_GUID")
            self.recording_processors.extend([
                BodyReplacerProcessor(keys=["alternateCallerId", "targets", "source", "callbackUri", "identity", "communicationUser", "rawId", "callConnectionId", "phoneNumber", "serverCallId"]),
                BodyReplacerProcessor(keys=["audioFileUri"], replacement = "https://dummy.ngrok.io/audio/sample-message.wav"),
                ResponseReplacerProcessor(keys=[self._resource_name]),
                RequestReplacerProcessor()])

        # create CallingServerClient
        endpoint, _ = parse_connection_str(self.connection_str)
        endpoint = endpoint

        if not is_live():
            credential = FakeTokenCredential()
        else:
            credential = DefaultAzureCredential()

        self.callingserver_client = CallingServerClient(
            endpoint,
            credential,
            http_logging_policy=get_http_logging_policy()
        )

        self.from_user = CallingServerLiveTestUtils.get_new_user_id(self.connection_str)
        self.to_user = CallingServerLiveTestUtils.get_new_user_id(self.connection_str)

    def test_create_play_cancel_hangup_scenario(self):
        # create call option and establish a call
        call_connection = self.callingserver_client.create_call_connection(
                    source=CommunicationUserIdentifier(self.from_user),
                    targets=[PhoneNumberIdentifier(self.to_phone_number)],
                    callback_uri=CONST.AppCallbackUrl,
                    requested_media_types=[CallMediaType.AUDIO],
                    requested_call_events=[CallingEventSubscriptionType.PARTICIPANTS_UPDATED],
                    alternate_caller_id=PhoneNumberIdentifier(self.from_phone_number)
                    )   
        CallingServerLiveTestUtils.validate_callconnection(call_connection)

        try:
            CallingServerLiveTestUtils.wait_for_operation_completion()
            # Get Call
            get_call_result = call_connection.get_call()
            assert get_call_result.call_connection_id is not None

            CallingServerLiveTestUtils.wait_for_operation_completion()
            OperationContext = str(uuid.uuid4())
            AudioFileId = str(uuid.uuid4())
            # Play Audio
            play_audio_result = call_connection.play_audio(
                CONST.AUDIO_FILE_URL,
                is_looped = True,
                audio_file_id = AudioFileId,
                operation_context = OperationContext
                )
            CallingServerLiveTestUtils.validate_play_audio_result(play_audio_result)

            CallingServerLiveTestUtils.wait_for_operation_completion()
            # Cancel All Media Operations
            call_connection.cancel_all_media_operations()
        except Exception as ex:
            print(str(ex))
        finally:
            # Hang up
            call_connection.hang_up()

    def test_create_add_remove_hangup_scenario(self):
        # create option and establish a call
        call_connection = self.callingserver_client.create_call_connection(
                    source=CommunicationUserIdentifier(self.from_user),
                    targets=[PhoneNumberIdentifier(self.to_phone_number)],
                    callback_uri=CONST.AppCallbackUrl,
                    requested_media_types=[CallMediaType.AUDIO],
                    requested_call_events=[CallingEventSubscriptionType.PARTICIPANTS_UPDATED],
                    alternate_caller_id=PhoneNumberIdentifier(self.from_phone_number)
                    )   

        CallingServerLiveTestUtils.validate_callconnection(call_connection)

        try:
            CallingServerLiveTestUtils.wait_for_operation_completion()
            added_participant = CallingServerLiveTestUtils.get_fixed_user_id(self.partcipant_guid)
            # Add Participant
            add_participant_result = call_connection.add_participant(
                participant=CommunicationUserIdentifier(added_participant)
                )
            CallingServerLiveTestUtils.validate_add_participant(add_participant_result)  
           
            CallingServerLiveTestUtils.wait_for_operation_completion()
            #list_participants 
            list_participants_result = call_connection.list_participants()
            assert len(list_participants_result) > 2

            # Remove Participant
            call_connection.remove_participant(CommunicationUserIdentifier(added_participant))
        except Exception as ex:
            print(str(ex))
        finally:
            # Hang up
            call_connection.hang_up()

    def test_test_create_add_play_audio_to_participant_remove_hangup_scenario(self):
        # create option and establish a call
        call_connection = self.callingserver_client.create_call_connection(
                    source=CommunicationUserIdentifier(self.from_user),
                    targets=[PhoneNumberIdentifier(self.to_phone_number)],
                    callback_uri=CONST.AppCallbackUrl,
                    requested_media_types=[CallMediaType.AUDIO],
                    requested_call_events=[CallingEventSubscriptionType.PARTICIPANTS_UPDATED],
                    alternate_caller_id=PhoneNumberIdentifier(self.from_phone_number)
                    )   
        CallingServerLiveTestUtils.validate_callconnection(call_connection)

        try:
            CallingServerLiveTestUtils.wait_for_operation_completion()
            added_participant = CallingServerLiveTestUtils.get_fixed_user_id(self.partcipant_guid)
            # Add Participant
            add_participant_result = call_connection.add_participant(
                participant=CommunicationUserIdentifier(added_participant)
                )
            CallingServerLiveTestUtils.validate_add_participant(add_participant_result)   

            CallingServerLiveTestUtils.wait_for_operation_completion()
            # Play Audio To Participant
            play_audio_to_participant_result = call_connection.play_audio_to_participant(
             participant=CommunicationUserIdentifier(added_participant), 
             audio_url = CONST.AUDIO_FILE_URL,
             is_looped=True,
             audio_file_id=str(uuid.uuid4()))    
             
            assert play_audio_to_participant_result.operation_id is not None   

            CallingServerLiveTestUtils.wait_for_operation_completion()
            # Cancel Participant Media Operation 
            call_connection.cancel_participant_media_operation(
                participant=CommunicationUserIdentifier(added_participant),
                media_operation_id=play_audio_to_participant_result.operation_id
            )

            # Remove Participant
            call_connection.remove_participant(CommunicationUserIdentifier(added_participant))

        except Exception as ex:
            print( str(ex))
        finally:
            # Hang up
            call_connection.hang_up()

    def test_create_add_participant_mute_unmute_hangup_scenario(self):
        # Establish a call
        call_connection = self.callingserver_client.create_call_connection(
                    source=CommunicationUserIdentifier(self.from_user),
                    targets=[PhoneNumberIdentifier(self.to_phone_number)],
                    callback_uri=CONST.AppCallbackUrl,
                    requested_media_types=[CallMediaType.AUDIO],
                    requested_call_events=[CallingEventSubscriptionType.PARTICIPANTS_UPDATED],
                    alternate_caller_id=PhoneNumberIdentifier(self.from_phone_number)
                    )   
        CallingServerLiveTestUtils.validate_callconnection(call_connection)

        try:
           # Add Participant
            CallingServerLiveTestUtils.wait_for_operation_completion()
            OperationContext = str(uuid.uuid4())
            added_participant = CallingServerLiveTestUtils.get_fixed_user_id(self.partcipant_guid)
            add_participant_result = call_connection.add_participant(
                participant=CommunicationUserIdentifier(added_participant),
                operation_context=OperationContext
                )
            CallingServerLiveTestUtils.validate_add_participant(add_participant_result)

            # Mute Participant
            call_connection.mute_participant(CommunicationUserIdentifier(added_participant))

            # Get Participant
            muted_participant = call_connection.get_participant(CommunicationUserIdentifier(added_participant))
            assert muted_participant.is_muted == True

            # Unmute Participant
            call_connection.unmute_participant(CommunicationUserIdentifier(added_participant))

            # Get Participant
            unmuted_participant = call_connection.get_participant(CommunicationUserIdentifier(added_participant))
            assert unmuted_participant.is_muted == False
           
            # Remove Participant
            call_connection.remove_participant(CommunicationUserIdentifier(added_participant))
        except Exception as ex:
            print(ex)
        finally:
            # Hang up
            call_connection.hang_up()  

    def test_hold_resume_participant_audio_scenario(self):
        # Establish a call
        call_connection = self.callingserver_client.create_call_connection(
                    source=CommunicationUserIdentifier(self.from_user),
                    targets=[PhoneNumberIdentifier(self.to_phone_number)],
                    callback_uri=CONST.AppCallbackUrl,
                    requested_media_types=[CallMediaType.AUDIO],
                    requested_call_events=[CallingEventSubscriptionType.PARTICIPANTS_UPDATED],
                    alternate_caller_id=PhoneNumberIdentifier(self.from_phone_number)
                    ) 

        CallingServerLiveTestUtils.validate_callconnection(call_connection)

        try:
            CallingServerLiveTestUtils.wait_for_operation_completion()
            OperationContext = str(uuid.uuid4())
            added_participant = CallingServerLiveTestUtils.get_fixed_user_id(self.partcipant_guid)
            participant=CommunicationUserIdentifier(added_participant)
            add_participant_result = call_connection.add_participant(
                participant=participant,
                operation_context=OperationContext
                )
            CallingServerLiveTestUtils.validate_add_participant(
                add_participant_result)

            CallingServerLiveTestUtils.wait_for_operation_completion()
            # Hold Participant
            call_connection.hold_participant_meeting_audio(participant)

            CallingServerLiveTestUtils.wait_for_operation_completion()
            # Resume Participant
            call_connection.resume_participant_meeting_audio(participant)

            # Remove Participant
            call_connection.remove_participant(participant)
        except Exception as ex:
            print(ex)
        finally:
            # Hang up
            call_connection.hang_up()

    @pytest.mark.skip("Skip test as it is not working now")
    def test_transfer_to_call_scenario(self):
        # create option and establish a call
        call_connection = self.callingserver_client.create_call_connection(
                    source=CommunicationUserIdentifier(self.from_user),
                    targets=[PhoneNumberIdentifier(self.to_phone_number)],
                    callback_uri=CONST.AppCallbackUrl,
                    requested_media_types=[CallMediaType.AUDIO],
                    requested_call_events=[CallingEventSubscriptionType.PARTICIPANTS_UPDATED],
                    alternate_caller_id=PhoneNumberIdentifier(self.from_phone_number)
                    )   
        CallingServerLiveTestUtils.validate_callconnection(call_connection)

        try:
            OperationContext = str(uuid.uuid4())
            # Transfer to call
            transfer_call_result = call_connection.transfer_to_call(
                target_call_connection_id = os.getenv("TARGET_CALL_CONNECTION_ID"),
                user_to_user_information='test information',
                operation_context=OperationContext
                )
            CallingServerLiveTestUtils.validate_transfer_call_participant(transfer_call_result)

        except Exception as ex:
            print(str(ex))

    def test_transfer_to_participant_scenario(self):
        # create option and establish a call
        call_connection = self.callingserver_client.create_call_connection(
                    source=CommunicationUserIdentifier(self.from_user),
                    targets=[PhoneNumberIdentifier(self.to_phone_number)],
                    callback_uri=CONST.AppCallbackUrl,
                    requested_media_types=[CallMediaType.AUDIO],
                    requested_call_events=[CallingEventSubscriptionType.PARTICIPANTS_UPDATED],
                    alternate_caller_id=PhoneNumberIdentifier(self.from_phone_number)
                    )   
        CallingServerLiveTestUtils.validate_callconnection(call_connection)

        try:
            OperationContext = str(uuid.uuid4())
            target_participant = CallingServerLiveTestUtils.get_fixed_user_id(self.partcipant_guid)
            # Transfer to participant
            transfer_call_result = call_connection.transfer_to_participant(
                target_participant=CommunicationUserIdentifier(target_participant),
                user_to_user_information='test information',
                operation_context=OperationContext
                )
            CallingServerLiveTestUtils.validate_transfer_call_participant(transfer_call_result)

        except Exception as ex:
            print(str(ex))

    def test_create_delete_keep_alive_scenario(self):
        # Establish a call
        call_connection = self.callingserver_client.create_call_connection(
                    source=CommunicationUserIdentifier(self.from_user),
                    targets=[PhoneNumberIdentifier(self.to_phone_number)],
                    callback_uri=CONST.AppCallbackUrl,
                    requested_media_types=[CallMediaType.AUDIO],
                    requested_call_events=[CallingEventSubscriptionType.PARTICIPANTS_UPDATED],
                    alternate_caller_id=PhoneNumberIdentifier(self.from_phone_number)
                    )   

        CallingServerLiveTestUtils.validate_callconnection(call_connection)

        # Check Keep Alive
        call_connection.keep_alive()

        CallingServerLiveTestUtils.wait_for_operation_completion()
        # Delete the call
        call_connection.delete()   # notice that call got disconnected
        try:
            CallingServerLiveTestUtils.wait_for_operation_completion()
            call_connection.keep_alive()
        except Exception as ex:
            assert '8522' in str(ex)

    @pytest.mark.skip("Skip test as it is not working now")
    def test_create_add_participant_audio_routing_scenario(self):
        # Establish a call
        call_connection = self.callingserver_client.create_call_connection(
                    source=CommunicationUserIdentifier(self.from_user),
                    targets=[PhoneNumberIdentifier(self.to_phone_number)],
                    callback_uri=CONST.AppCallbackUrl,
                    requested_media_types=[CallMediaType.AUDIO],
                    requested_call_events=[CallingEventSubscriptionType.PARTICIPANTS_UPDATED],
                    alternate_caller_id=PhoneNumberIdentifier(self.from_phone_number)
                    )   

        CallingServerLiveTestUtils.validate_callconnection(call_connection)

        CallingServerLiveTestUtils.wait_for_operation_completion()

        try:
            OperationContext = str(uuid.uuid4())
            added_participant = CallingServerLiveTestUtils.get_fixed_user_id(self.partcipant_guid)
            # Add Participant
            add_participant_result = call_connection.add_participant(
                participant=CommunicationUserIdentifier(added_participant),
                operation_context=OperationContext
                )

            CallingServerLiveTestUtils.validate_add_participant(add_participant_result)

            CallingServerLiveTestUtils.wait_for_operation_completion()
            
            participants_list = [] 
            participants_list.append(CommunicationUserIdentifier(added_participant))
            # Create Audio Routing Group 
            create_audio_routing_group_result = call_connection.create_audio_routing_group(audio_routing_mode=AudioRoutingMode.MULTICAST,
                    targets=participants_list)

            CallingServerLiveTestUtils.validate_create_audio_routing_group(create_audio_routing_group_result)

            audioRoutingGroupId = create_audio_routing_group_result.audio_routing_group_id

            # Get Audio Routing Group
            get_audio_routing_group_result = call_connection.list_audio_routing_groups(audioRoutingGroupId)
            assert get_audio_routing_group_result.audio_routing_mode == AudioRoutingMode.MULTICAST
            assert get_audio_routing_group_result.targets[0].raw_id == added_participant

            OperationContext = str(uuid.uuid4())
            added_another_participant = CallingServerLiveTestUtils.get_fixed_user_id(self.another_partcipant_guid)
            # Add Another Participant
            add_another_participant_result = call_connection.add_participant(
                participant=CommunicationUserIdentifier(added_another_participant),
                operation_context=OperationContext
                )

            CallingServerLiveTestUtils.validate_add_participant(add_another_participant_result)
            CallingServerLiveTestUtils.wait_for_operation_completion()

            participant_list = [] 
            participant_list.append(CommunicationUserIdentifier(added_another_participant))
            # Update Audio Routing Group
            call_connection.update_audio_routing_group(audioRoutingGroupId, participant_list)

            # Get Audio Routing Group
            get_audio_routing_group_result = call_connection.list_audio_routing_groups(audioRoutingGroupId)
            assert get_audio_routing_group_result.audio_routing_mode == AudioRoutingMode.MULTICAST
            assert get_audio_routing_group_result.targets[0].raw_id == added_another_participant

            # Delete Audio Routing Group
            call_connection.delete_audio_routing_group(audioRoutingGroupId)

            # Remove Participant
            call_connection.remove_participant(CommunicationUserIdentifier(added_participant))
        except Exception as ex:
            print( str(ex))
        finally:
            # Hang up
            call_connection.hang_up()